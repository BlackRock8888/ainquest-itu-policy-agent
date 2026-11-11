"""Machine-readable mapping of this module to ITU-T Y.3172 pipeline nodes and
ITU AI Readiness Framework 2.0 dimensions.

Node and dimension identifiers are taken from the ITU reference code
(github.com/CrashingGuru/ITUAIReadiness @ 84010da, MIT):
  simulation/server/agents/usecase.py  (Y3172_PIPELINE_NODES, NODE_TO_DIMENSIONS)
  simulation/data/framework/dimensions.json
The mapping of OUR components to those nodes is our own claim, to be
checked by reviewers; it is not an ITU certification.
"""
from __future__ import annotations

REFERENCE = {"repo": "https://github.com/CrashingGuru/ITUAIReadiness", "commit": "84010da9e9c443afcceeccb86d1700a662223395",
             "license": "MIT"}

# copied from reference usecase.py NODE_TO_DIMENSIONS
NODE_TO_DIMENSIONS = {
    "SRC": [1, 4, 13], "C": [1, 3, 13], "PP": [1, 2, 3], "M": [2, 3, 5, 9],
    "P": [7, 8, 10], "D": [5, 6, 12], "SINK": [5, 6, 12, 13], "MLFO": [5, 7, 8], "Sandbox": [10, 11],
}

COMPONENTS = [
    {"node": "SRC", "component": "Default synthetic kb/; separate opt-in UNESCO guidance subset in kb_candidates/unesco/; research-source index is metadata only",
     "status": "one default synthetic card; three separately licensed global_nonbinding guidance cards; remaining research corpus withheld"},
    {"node": "C", "component": "scripts/build_kb.py (collector: verbatim quotes + snapshot verification)", "status": "research checkout only; excluded from synthetic public export"},
    {"node": "PP", "component": "Card annotation (scope, level, authority tier, topics), glossary-based EN/RU/AR query expansion, normalisation (src/policy_agent/text.py, scope.py)",
     "status": "implemented; RU/AR glossary not native-reviewed"},
    {"node": "M", "component": "BM25 retrieval + evidence gate (retrieve.py, evidence.py). Optional local LLM (Ollama) only rephrases gated evidence.",
     "status": "retrieval implemented; LLM path implemented but NOT run; no fine-tuning"},
    {"node": "P", "component": "Policy node: scope filter, authority tiers (binding vs non-binding vs foreign), curated source-boundary refusal (not universal), detector-not-proof rule, human review flag",
     "status": "implemented"},
    {"node": "D", "component": "Answer object: language-localised frame, original-language quotes, citations, unknowns, conflicts", "status": "implemented"},
    {"node": "SINK", "component": "CLI / JSON for a student, teacher or policy officer; decision log runs/*.jsonl", "status": "implemented (CLI only, no UI)"},
    {"node": "MLFO", "component": "Session/replay orchestrator for progressive events (replay.py)", "status": "implemented, single agent"},
    {"node": "Sandbox", "component": "Offline eval + replay harness (evaluate.py, evals/). ITU sandbox / cloud credits not used.",
     "status": "local only; ITU sandbox access not confirmed"},
]

# Dimension names from reference dimensions.json (framework 2.0)
DIMENSIONS = {1: "Data/Model Marketplace", 2: "Generated Content Marketplace", 3: "Cross-Domain Correlation Analysis",
              4: "Contextualization and Regional Impact", 5: "Level of Integration of AI in Workflows", 6: "Human Interface",
              7: "Strategy Alignment", 8: "Collaboration with AI", 9: "Impacts of Humans in AI Integration",
              10: "AI & Policies", 11: "AI for Inclusion", 12: "Granular Priorities", 13: "Digital Infrastructure"}

# Our own primary claims (subset), with the artefact that evidences each.
DIMENSION_CLAIMS = {
    4: "Scope fields (jurisdiction / institution / level) on every card; UAE-specific scope applies to the withheld research corpus; default KB is synthetic and the separate UNESCO subset is global_nonbinding",
    6: "Answers in the user's language (EN/RU/AR) with original-language quotes",
    7: "Withheld research corpus only: cards from UAE AI Strategy 2031 and UAE AI Charter linked to education rules; not present in the public KB",
    9: "Human-review flag; detector score never treated as proof",
    10: "Scope-conflict flags; policy gap candidates and public/research boundaries are documented in docs/standards-mapping.md#gaps; substantive policy contradictions require review",
    11: "EN/RU/AR query expansion and templates; default synthetic demo plus opt-in UNESCO guidance subset; three context-only examples passed, native language review remains pending",
}


def mapping() -> dict:
    return {"reference": REFERENCE, "y3172": [dict(c, dimensions=NODE_TO_DIMENSIONS[c["node"]]) for c in COMPONENTS],
            "dimension_claims": {f"{k} {DIMENSIONS[k]}": v for k, v in DIMENSION_CLAIMS.items()}}
