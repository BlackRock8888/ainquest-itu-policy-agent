"""Lexical BM25 retrieval over cards + explicit scope filter.

Retrieval is deliberately separated from the evidence gate and from answer
composition, so each stage can be measured on its own (recall@k vs. gate
decisions vs. answer content).
"""
from __future__ import annotations

import math
from collections import Counter

from .scope import Scope
from .text import content_tokens

K1, B = 1.4, 0.75
LEVEL_OK = {
    None: {"k12", "higher_ed", "graduate", "all", "national"},
    "k12": {"k12", "all", "national"},
    "higher_ed": {"higher_ed", "all", "national"},
    "graduate": {"graduate", "higher_ed", "all", "national"},
}


def card_text(card: dict, source: dict) -> str:
    return " ".join([card["quote"], " ".join(card["topics"]), source["title"], source["publisher"]])


def scope_filter(card: dict, sc: Scope) -> tuple[bool, str]:
    """Return (eligible, applicability) where applicability in
    applies | applies_if_scope_confirmed | context_only | out_of_scope."""
    if card["jurisdiction"] in ("global", "EU"):
        return True, "context_only"
    if card["level"] not in LEVEL_OK.get(sc.level, LEVEL_OK[None]):
        return False, "out_of_scope"
    if card["institution"]:
        if sc.institution is None:
            return True, "applies_if_scope_confirmed"
        if card["institution"] != sc.institution:
            return False, "out_of_scope"
    if card["jurisdiction"] in ("Abu Dhabi", "Dubai", "Sharjah"):
        if sc.emirate and sc.emirate != card["jurisdiction"]:
            return False, "out_of_scope"
        if not sc.emirate:
            return True, "applies_if_scope_confirmed"
    if card["institution"] and sc.institution == card["institution"]:
        if card["level"] == "graduate" and sc.level not in ("graduate",):
            return True, "applies_if_scope_confirmed"
        return True, "applies"
    if card["authority_tier"] >= 4:
        return True, "context_only"
    return True, "applies" if sc.level else "applies_if_scope_confirmed"


def bm25_rank(cards: list[dict], sources: dict, query_terms: list[str]) -> list[tuple[float, dict]]:
    docs = [content_tokens(card_text(c, sources[c["source_id"]])) for c in cards]
    if not docs:
        return []
    avg = sum(map(len, docs)) / len(docs)
    df = Counter(t for d in docs for t in set(d))
    n = len(docs)
    q = Counter(query_terms)
    scored = []
    for c, d in zip(cards, docs):
        tf = Counter(d)
        s = 0.0
        for t in q:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * len(d) / avg))
        scored.append((s, c))
    scored.sort(key=lambda x: (-x[0], x[1]["card_id"]))
    return scored


def retrieve(cards: list[dict], sources: dict, sc: Scope, k: int = 8) -> list[dict]:
    terms = content_tokens(sc.original_query) + [t for w in sc.expansion for t in content_tokens(w)]
    terms += [t for topic in sc.topics for t in content_tokens(topic.replace("_", " "))]
    out = []
    for score, c in bm25_rank(cards, sources, terms):
        ok, applicability = scope_filter(c, sc)
        topic_hit = bool(set(c["topics"]) & sc.topics)
        if score <= 0 and not topic_hit:
            continue
        out.append({"card": c, "bm25": round(score, 4), "eligible": ok,
                    "applicability": applicability, "topic_match": topic_hit})
    # topic-matched and eligible first, then score. Ineligible topic matches are
    # kept (flagged) so the gate can explain WHY a known source does not apply.
    out.sort(key=lambda r: (not r["eligible"], not r["topic_match"], -r["bm25"], r["card"]["card_id"]))
    eligible = [r for r in out if r["eligible"]][:k]
    excluded = [r for r in out if not r["eligible"] and r["topic_match"]]
    return eligible + excluded
