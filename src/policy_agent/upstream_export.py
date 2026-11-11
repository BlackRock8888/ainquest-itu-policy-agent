"""Export the KB in the format the ITU reference ingestion expects.

Reference: simulation/server/knowledge/ingest.py ingests .txt/.md/.pdf files
recursively from InputDocs/, using the sub-folder as `document_category`
and inferring `country` from the FILE NAME. The reference _COUNTRY_PATTERNS
has no UAE pattern, so UAE files would be tagged "global". We therefore put
"UAE" in every file name and ship a one-line patch suggestion.

Each exported file contains only metadata and the short verbatim quotes we
use (not full documents), with the source URL for attribution.
"""
from __future__ import annotations

import json
from pathlib import Path

from .kb import KB

PATCH = '''# Suggested 1-line patch for simulation/server/knowledge/ingest.py, _COUNTRY_PATTERNS:
    (r"(?i)UAE|Emirat|Abu_?Dhabi|Dubai|Sharjah|ADEK|KHDA|SPEA", "United Arab Emirates"),
'''


def export(kb: KB, out_dir: Path) -> dict:
    target = out_dir / "InputDocs" / "AI_Strategies" / "UAE_AI_Education"
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for sid, s in sorted(kb.sources.items()):
        cards = [c for c in kb.cards if c["source_id"] == sid]
        prefix = "UAE_" if s["jurisdiction"] not in ("global", "EU") else "REF_"
        name = f"{prefix}{sid}.txt"
        lines = [f"Title: {s['title']}", f"Publisher: {s['publisher']}", f"URL: {s['url']}",
                 f"Jurisdiction: {s['jurisdiction']}", f"Institution: {s.get('institution') or '-'}",
                 f"Level: {s['level']}", f"Binding status: {s['binding_status']} ({s.get('binding_evidence') or 'not supplied; no authority inferred'})",
                 f"Publication date: {s.get('publication_date') or 'not printed'}",
                 f"Fetched (UTC): {s['fetched_at_utc']}", f"Caveats: {s.get('caveats') or '-'}",
                 f"Licence note: {s.get('license_note')}", "", "Verbatim excerpts:"]
        lines += [f"[{c['card_id']}] \"{c['quote']}\" (topics: {', '.join(c['topics'])}; rule: {c['rule_type']})" for c in cards]
        (target / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(name)
    (out_dir / "UPSTREAM_PATCH_country_pattern.txt").write_text(PATCH, encoding="utf-8")
    (out_dir / "manifest.json").write_text(json.dumps({"corpus_sha256": kb.corpus_sha256, "files": written}, indent=1))
    return {"dir": str(target), "files": len(written), "corpus_sha256": kb.corpus_sha256}
