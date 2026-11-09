import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from policy_agent.kb import load_kb
from policy_agent.agent import answer
def test_synthetic_disclosure():
    r=answer("What disclosure is required at Demo University for an assignment?",load_kb())
    assert r["citations"] and r["citations"][0]["card_id"]=="DEMO_AI_POLICY#1"
    assert "SYNTHETIC" in r["citations"][0]["quote"]
def test_missing_policy():
    r=answer("Can I use AI for my thesis at Zayed University?",load_kb())
    assert r["decision"]=="refuse" and not r["citations"]
