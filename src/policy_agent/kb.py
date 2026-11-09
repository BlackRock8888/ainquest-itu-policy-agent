"""Knowledge-base loading. Read-only; expected answers (test labels) are never loaded here."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[2] / "kb"


@dataclass
class KB:
    cards: list[dict]
    sources: dict[str, dict]
    glossary: dict
    corpus_sha256: str
    superseded: set[str] = field(default_factory=set)

    def active_cards(self, visible: set[str] | None = None) -> list[dict]:
        out = []
        for c in self.cards:
            if c["card_id"] in self.superseded:
                continue
            if visible is not None and c["source_id"] not in visible:
                continue
            out.append(c)
        return out


def load_kb(kb_dir: Path = KB_DIR) -> KB:
    raw = (kb_dir / "cards.jsonl").read_text(encoding="utf-8")
    cards = [json.loads(l) for l in raw.splitlines() if l.strip()]
    sources = {}
    for l in (kb_dir / "sources.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            s = json.loads(l)
            sources[s["id"]] = s
    glossary = json.loads((kb_dir / "glossary.json").read_text(encoding="utf-8"))
    return KB(cards=cards, sources=sources, glossary=glossary,
              corpus_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest())
