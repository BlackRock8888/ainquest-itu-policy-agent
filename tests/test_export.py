"""Regression for exporting the public fixture without optional authority evidence."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from policy_agent.kb import load_kb
from policy_agent.upstream_export import export


def test_public_export_without_binding_evidence():
    kb = load_kb()
    assert "binding_evidence" not in kb.sources["DEMO_AI_POLICY"]
    with tempfile.TemporaryDirectory(prefix="itu-public-export-") as directory:
        target = Path(directory)
        result = export(kb, target)
        manifest = json.loads((target / "manifest.json").read_text())
        assert result["files"] == 1
        assert manifest["corpus_sha256"] == kb.corpus_sha256
        exported = (Path(result["dir"]) / manifest["files"][0]).read_text()
        assert "synthetic_test_only (not supplied; no authority inferred)" in exported
        assert "SYNTHETIC TEST RULE" in exported
        assert "https://example.invalid/synthetic-policy" in exported
