"""Scope extraction: who/where/what level/which topic, from the ORIGINAL query.

The original query is kept unchanged; expansion terms are derived from it,
never substituted for it. Explicit scope passed by the caller (e.g. from an
earlier turn or an event) overrides what is inferred from text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .text import detect_lang, normalise, stemmed

TOPIC_CONCEPTS = ("exam", "assignment", "disclosure", "detector", "penalty", "syllabus",
                  "age_limit", "emotion_recognition", "data_protection", "curriculum", "price")
LEVEL_CONCEPTS = {"school": "k12", "university": "higher_ed", "graduate": "graduate"}


@dataclass
class Scope:
    original_query: str
    lang: str
    institution: str | None = None
    unknown_institution: str | None = None
    emirate: str | None = None
    level: str | None = None
    topics: set[str] = field(default_factory=set)
    concepts: set[str] = field(default_factory=set)
    expansion: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"lang": self.lang, "institution": self.institution,
                "unknown_institution": self.unknown_institution, "emirate": self.emirate,
                "level": self.level, "topics": sorted(self.topics), "conflicts": self.conflicts}


def _find_aliases(text: str, alias_map: dict[str, list[str]]) -> list[tuple[str, int, int]]:
    """Longest-alias-first matching on stemmed word sequences; matched spans are consumed."""
    t = " " + " ".join(stemmed(text)) + " "
    pairs = sorted(((" ".join(stemmed(a)), name) for name, al in alias_map.items() for a in al),
                   key=lambda p: -len(p[0]))
    taken: list[tuple[int, int]] = []
    hits = []
    for alias, name in pairs:
        for m in re.finditer(r"(?<= )" + re.escape(alias) + r"(?= )", t):
            s, e = m.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            hits.append((name, s, e))
    return hits


def extract_scope(query: str, glossary: dict, explicit: dict | None = None) -> Scope:
    sc = Scope(original_query=query, lang=detect_lang(query))
    toks = set(stemmed(query))
    for concept, langs in glossary["terms"].items():
        vocab = {st for ws in langs.values() for w in ws for st in stemmed(w)}
        if toks & vocab:
            sc.concepts.add(concept)
            sc.expansion.extend(langs["en"])
    sc.topics = {c for c in sc.concepts if c in TOPIC_CONCEPTS}
    # "use AI for an assignment" with no other topic = a permission question
    if sc.topics <= {"assignment"} and ({"assignment", "permission"} & sc.concepts):
        sc.topics.add("permission")

    inst = {h[0] for h in _find_aliases(query, glossary["institution_aliases"])}
    if len(inst) > 1:
        sc.conflicts.append("multiple_institutions:" + "|".join(sorted(inst)))
    elif inst:
        sc.institution = inst.pop()
    nq = " " + " ".join(stemmed(query)) + " "
    for marker in glossary.get("unknown_institution_markers", []):
        if " " + " ".join(stemmed(marker)) + " " in nq:
            sc.unknown_institution = marker
    em = {h[0] for h in _find_aliases(query, glossary["emirate_aliases"])}
    if len(em) == 1:
        sc.emirate = em.pop()

    levels = {LEVEL_CONCEPTS[c] for c in sc.concepts if c in LEVEL_CONCEPTS}
    if "graduate" in levels:
        levels.discard("higher_ed")
    if "k12" in levels and len(levels) > 1:
        sc.conflicts.append("level_conflict:" + "|".join(sorted(levels)))
    elif len(levels) == 1:
        sc.level = levels.pop()
    elif levels:
        sc.level = sorted(levels)[0]
    if sc.institution and sc.level is None:
        sc.level = "higher_ed"  # all three known institutions are universities

    for k, v in (explicit or {}).items():
        if v is not None and hasattr(sc, k):
            setattr(sc, k, set(v) if k == "topics" else v)
    return sc
