"""Explicitly load the separately licensed UNESCO subset; never change the default KB."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from policy_agent.agent import answer
from policy_agent.kb import load_kb

bundle = root / "kb_candidates" / "unesco"
manifest = json.loads((bundle / "MANIFEST_SHA256.json").read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((bundle / name).read_bytes()).hexdigest() == digest, name
kb = load_kb(bundle / "kb")
assert len(kb.cards) == 3 and len(kb.sources) == 1
assert kb.corpus_sha256 == (bundle / "kb" / "CORPUS_SHA256").read_text().strip()
assert all(c["jurisdiction"] == "global" and c["binding_status"] == "global_nonbinding" for c in kb.cards)
queries = [
    ("en", "What minimum age does UNESCO recommend for independent conversations with GenAI platforms?"),
    ("ru", "Какой минимальный возраст рекомендует UNESCO для самостоятельного общения с генеративным ИИ?"),
    ("ar", "ما الحد الأدنى للعمر الذي توصي به اليونسكو للمحادثات المستقلة مع الذكاء الاصطناعي التوليدي؟"),
]
by_id = {c["card_id"]: c for c in kb.cards}
results = []
for lang, query in queries:
    result = answer(query, kb)
    assert result["decision"] == "context_only" and not result["citations"]
    assert result["lang"] == lang and result["context_examples"]
    assert any(c["card_id"] == "UNESCO_GENAI_GUIDANCE_2023#1" for c in result["context_examples"])
    for cited in result["context_examples"]:
        original = by_id[cited["card_id"]]
        assert cited["quote"] == original["quote"]
        assert cited["binding_status"] == "global_nonbinding"
        cited.update({key: original[key] for key in ("attribution", "license_url", "source_page_pdf", "source_page_printed", "context_note")})
    results.append({"query": query, "result": result})

print(json.dumps({
    "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "kind": "Three author-defined context-only checks; not independent evaluation or UAE legal guidance",
    "corpus_sha256": kb.corpus_sha256,
    "checks_passed": len(results),
    "source_count": len(kb.sources),
    "card_count": len(kb.cards),
    "notices_path": "kb_candidates/unesco/THIRD_PARTY_NOTICES.md",
    "notices": (bundle / "THIRD_PARTY_NOTICES.md").read_text(),
    "results": results,
}, ensure_ascii=False, indent=2))
