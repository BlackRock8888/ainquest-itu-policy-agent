# AINQUEST ITU policy-agent research prototype

Public, sanitized code snapshot for review. **Not a production adviser, legal opinion, ITU certification, accepted entry, or completed submission.**

## Run offline
Python 3.10+. No credentials needed.
```sh
PYTHONPATH=src python -m policy_agent ask "What disclosure is required at Demo University for an assignment?"
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
```

## Included and excluded
The Python engine implements lexical retrieval, scope filtering, an evidence gate, structured decision records, evaluation and replay harnesses. The bundled KB contains ONE **invented synthetic rule**, not UAE policy. Real-source metadata is listed separately, without source quotations or document copies. The public demo does not reproduce the research-corpus metrics below. Original snapshots, quotations, private chat links, personal information, credentials, production code and original git history are intentionally excluded.

## Recorded research results, not public-demo results
Original research corpus: 16 sources / 49 cards. Baseline external-model-authored adversarial set: **2/20 strict pass**. After targeted safety fixes on already exposed tests: **3/20 strict pass**, decision-only **9/20**. This is regression, NOT a fresh held-out estimate. Same-author dev 20/20 and old heldout 14/15 do not demonstrate generalization. Targeted safety regression 14/14; local pytest 26 passed / 1 skipped (reference-ingest compatibility not rerun). These aggregates were read from local artifacts; the source corpus is withheld pending redistribution review. Do not combine denominators or call this independent validation.

## Limitations
Curated missing-document matching is not comprehensive. RU/AR language output and glossary are not native-reviewed. LLM path is implemented but untested. No fine-tuning, sandbox deployment or production readiness is claimed. Three of twenty adversarial cases passing remains poor.

## Submission status
Official event page, checked 2026-11-09: deadline 10 November 2026; technical report max 5 pages, GitHub repository, policy/regulation/strategy KB; first-round demo video optional (max 7 minutes). Applications page says closed. Exact submission channel/cutoff and eligibility are not confirmed here. This synthetic-only public KB is NOT claimed to fulfil the competition's policy-KB requirement.
https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/

## Attribution and rights
`standards.py` contains a mapping derived from ITUAIReadiness commit 84010da9e9c443afcceeccb86d1700a662223395; its MIT notice is reproduced in THIRD_PARTY_NOTICES.md. Other original project code is published for inspection; no additional reuse license is granted yet. Original authors retain their rights.
