"""Progressive (chunked) event scenarios — the ITU "error scenario" requirement.

Events arrive one at a time and may be incomplete. The session carries scope
(institution, level, emirate) across turns, so changing the query language
must not change the applicable rules. Expected outcomes live in the scenario
file under "expect" and are NEVER passed to the agent; the runner compares
afterwards.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .agent import answer
from .audit import new_run_id, utc_now, write_record
from .kb import KB

REQUIRED = {"user_message": ["text"], "document": ["doc_type", "content"],
            "supersede": ["card_ids", "note"], "signal": ["signal_type", "text"]}
CARRY = ("institution", "level", "emirate")


class Session:
    def __init__(self, kb: KB, log_path: Path | None):
        self.kb = copy.deepcopy(kb)
        self.log_path = log_path
        self.scope: dict = {}
        self.context_docs: dict = {}
        self.changes: list[str] = []
        self.pending_signal: str | None = None
        self.run_id = new_run_id()

    def handle(self, ev: dict) -> dict:
        etype = ev.get("type")
        missing = [f for f in REQUIRED.get(etype, ["?"]) if f not in ev.get("payload", {})]
        if etype not in REQUIRED or missing or ev.get("partial"):
            rec = {"run_id": self.run_id, "event_id": ev.get("id"), "utc": utc_now(),
                   "terminal": "partial", "reason": f"incomplete_event:{etype}:{missing or 'flagged_partial'}"}
            write_record(self.log_path, rec)
            return {"event_id": ev.get("id"), "terminal": "partial", "decision": None, "reason": rec["reason"]}
        p = ev["payload"]
        if etype == "document":
            self.context_docs[p["doc_type"]] = {"content": p["content"], "synthetic": p.get("synthetic", False),
                                                "source_note": p.get("source_note")}
            write_record(self.log_path, {"run_id": self.run_id, "event_id": ev["id"], "utc": utc_now(),
                                         "terminal": "complete", "state_change": f"context_doc:{p['doc_type']}"})
            return {"event_id": ev["id"], "terminal": "complete", "decision": "state_updated"}
        if etype == "supersede":
            self.kb.superseded |= set(p["card_ids"])
            self.changes.append(f"superseded:{','.join(p['card_ids'])}:{p['note']}")
            write_record(self.log_path, {"run_id": self.run_id, "event_id": ev["id"], "utc": utc_now(),
                                         "terminal": "complete", "state_change": self.changes[-1]})
            return {"event_id": ev["id"], "terminal": "complete", "decision": "state_updated"}
        if etype == "signal":
            self.pending_signal = p["text"]
            text = p["text"]
        else:
            text = p["text"]
        out = answer(text, self.kb, explicit_scope=self._carry(text), context_docs=self.context_docs,
                     log_path=self.log_path, event_id=ev["id"], run_id=self.run_id)
        for k in CARRY:
            if out["scope"].get(k):
                self.scope[k] = out["scope"][k]
        if self.context_docs.get("syllabus"):
            d = self.context_docs["syllabus"]
            out["user_provided_documents"] = [{"doc_type": "syllabus", "content": d["content"],
                                               "synthetic": d["synthetic"], "note": d["source_note"]}]
        if self.changes:
            out["version_changes"] = list(self.changes)
        out["event_id"] = ev["id"]
        out["terminal"] = "complete"
        return out

    def _carry(self, text: str) -> dict:
        from .scope import extract_scope
        fresh = extract_scope(text, self.kb.glossary)
        return {k: v for k, v in self.scope.items() if getattr(fresh, k) is None}


def run_scenario(path: Path, kb: KB, log_path: Path | None) -> list[dict]:
    sc = json.loads(path.read_text(encoding="utf-8"))
    sess = Session(kb, log_path)
    return [sess.handle({k: v for k, v in ev.items() if k != "expect"}) for ev in sc["events"]]


def check(results: list[dict], scenario: dict) -> list[dict]:
    """Compare outputs with scenario expectations (outside the agent)."""
    report = []
    for res, ev in zip(results, scenario["events"]):
        exp = ev.get("expect", {})
        fails = []
        if "terminal" in exp and res.get("terminal") != exp["terminal"]:
            fails.append(f"terminal {res.get('terminal')}!={exp['terminal']}")
        if "decision" in exp and res.get("decision") != exp["decision"]:
            fails.append(f"decision {res.get('decision')}!={exp['decision']}")
        cited = {c["source_id"] for c in res.get("citations", [])}
        cited_cards = {c["card_id"] for c in res.get("citations", []) + res.get("context_examples", [])}
        for s in exp.get("must_cite_sources", []):
            if s not in cited:
                fails.append(f"missing source {s}")
        for c in exp.get("must_not_cite_cards", []):
            if c in cited_cards:
                fails.append(f"cited superseded/forbidden {c}")
        for u in exp.get("must_have_unknowns", []):
            if u not in res.get("unknowns", []):
                fails.append(f"missing unknown {u}")
        for u in exp.get("must_not_have_unknowns", []):
            if u in res.get("unknowns", []):
                fails.append(f"unexpected unknown {u}")
        if exp.get("human_review_required") and not res.get("human_review_required"):
            fails.append("human review not flagged")
        if exp.get("version_change_reported") and not res.get("version_changes"):
            fails.append("version change not reported")
        if "lang" in exp and res.get("lang") != exp["lang"]:
            fails.append(f"lang {res.get('lang')}!={exp['lang']}")
        report.append({"event_id": ev["id"], "pass": not fails, "fails": fails})
    return report
