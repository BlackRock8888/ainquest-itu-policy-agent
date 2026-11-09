"""Offline evaluation. Expected answers are read here only, after the agent ran.

Metrics are reported separately, never merged into one score:
  retrieval_recall@k  - expected sources among retrieved cards (before the gate)
  decision_accuracy   - answer / context_only / clarify / refuse
  citation_ok         - required sources cited, forbidden sources not cited
  cross_lingual_consistency - same decision + same cited sources across EN/RU/AR in a group
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .agent import answer
from .kb import KB
from .retrieve import retrieve
from .scope import extract_scope


def load_items(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def evaluate(items: list[dict], kb: KB, log_path: Path | None = None) -> dict:
    rows, by_group = [], defaultdict(list)
    for it in items:
        out = answer(it["query"], kb, log_path=log_path, event_id=it["id"])
        sc = extract_scope(it["query"], kb.glossary)
        retrieved_sources = {r["card"]["source_id"] for r in retrieve(kb.active_cards(), kb.sources, sc)}
        exp = it["expect"]
        cited = {c["source_id"] for c in out["citations"]}
        ctx = {c["source_id"] for c in out["context_examples"]}
        expected_sources = set(exp.get("must_cite_sources", [])) | set(exp.get("must_cite_context", []))
        fails = []
        if out["decision"] != exp["decision"]:
            fails.append(f"decision {out['decision']}!={exp['decision']}")
        for s in exp.get("must_cite_sources", []):
            if s not in cited:
                fails.append(f"missing {s}")
        for s in exp.get("must_cite_context", []):
            if s not in ctx | cited:
                fails.append(f"missing context {s}")
        for s in exp.get("must_not_cite_sources", []):
            if s in cited:
                fails.append(f"forbidden {s}")
        for u in exp.get("must_have_unknowns", []):
            if u not in out["unknowns"]:
                fails.append(f"missing unknown {u}")
        if exp.get("human_review_required") and not out["human_review_required"]:
            fails.append("human review not flagged")
        row = {"id": it["id"], "group": it["group"], "lang": it["lang"], "detected_lang": out["lang"],
               "decision": out["decision"], "reason": out["reason"], "cited": sorted(cited),
               "context": sorted(ctx), "unknowns": out["unknowns"], "latency_ms": out["latency_ms"],
               "retrieval_hit": (expected_sources <= retrieved_sources) if expected_sources else None,
               "pass": not fails, "fails": fails}
        rows.append(row)
        by_group[it["group"]].append(row)

    def rate(xs):
        xs = [x for x in xs if x is not None]
        return {"n": len(xs), "ok": sum(xs), "rate": round(sum(xs) / len(xs), 3) if xs else None}

    consistency = {}
    for g, rs in by_group.items():
        if len({r["lang"] for r in rs}) > 1:
            consistency[g] = len({(r["decision"], tuple(r["cited"])) for r in rs}) == 1
    per_lang = {}
    for lang in sorted({r["lang"] for r in rows}):
        rs = [r for r in rows if r["lang"] == lang]
        per_lang[lang] = {"pass": rate([r["pass"] for r in rs]),
                          "retrieval_recall": rate([r["retrieval_hit"] for r in rs]),
                          "decision": rate([not any(f.startswith("decision") for f in r["fails"]) for r in rs])}
    return {
        "corpus_sha256": kb.corpus_sha256,
        "items": len(rows),
        "overall_pass": rate([r["pass"] for r in rows]),
        "retrieval_recall_at_8": rate([r["retrieval_hit"] for r in rows]),
        "decision_accuracy": rate([not any(f.startswith("decision") for f in r["fails"]) for r in rows]),
        "citation_ok": rate([not any(f.startswith(("missing", "forbidden")) for f in r["fails"]) for r in rows]),
        "cross_lingual_consistency": {"groups": consistency, **rate(list(consistency.values()))},
        "per_lang": per_lang,
        "rows": rows,
    }
