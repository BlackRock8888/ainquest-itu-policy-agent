# AINQUEST ITU policy-agent research prototype

Public, sanitized research prototype for review. **Not a production adviser, legal opinion, ITU certification or confirmed accepted entry.** The default demonstration uses one invented rule. A separate explicitly loaded UNESCO subset supplies three licensed global-guidance excerpts. Submission correspondence and technical readiness are separate statuses.

The supplementary [five-page technical report (PDF)](reports/ITU_Technical_Report_AINQUEST_2026-11-12.pdf), [editable report (DOCX)](reports/ITU_Technical_Report_AINQUEST_2026-11-12.docx) and [delivery manifest](reports/DELIVERY_MANIFEST.json) describe the 12 November package. See [development milestones](docs/ROADMAP.md) for the remaining research work.

## Run offline
Python 3.10+. No credentials needed for the deterministic path. From the repository root:
```sh
PYTHONPATH=src python -m policy_agent ask "What disclosure is required at Demo University for an assignment?"
PYTHONPATH=src python -m policy_agent eval evals/synthetic-smoke.jsonl --out runs/synthetic-smoke.json
PYTHONPATH=src python -m policy_agent replay evals/scenarios/synthetic-progressive.json --out runs/synthetic-replay.json
PYTHONPATH=src python -m policy_agent standards
PYTHONPATH=src python -m policy_agent export-upstream runs/synthetic-export
python scripts/check_public_demo.py
```
The last command runs the two original smoke checks and the export regression using the Python standard library. For pytest users:
```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
```
The bundled assessment has six author-defined synthetic smoke cases. The progressive replay has eight events (incomplete input, language changes, receipt of a synthetic document, an unsupported signal and withdrawal of the only card). They demonstrate execution and expected mechanics; they are not independent evaluation, legal validation or a test on real UAE policy. See [VALIDATION.md](VALIDATION.md) for exact results and [standards mapping](docs/standards-mapping.md) for the implementation boundary.

## Included and excluded
The Python engine implements lexical retrieval, scope filtering, an evidence gate, structured decision records, evaluation and replay harnesses. The default `kb/` contains ONE **invented synthetic rule**, not UAE policy. The 16-entry research-source index is metadata only. A distinct `kb_candidates/unesco/` bundle contains three licensed excerpts from one UNESCO publication; it is loaded only by explicit path and never merged into the default demo. The public package does not reproduce the research-corpus metrics below. Other research quotations and source snapshots, private chat links, personal information, credentials, production code and original git history remain excluded.

## Separately licensed UNESCO guidance subset

```sh
python scripts/check_unesco_candidate.py
```

This runner verifies the recovered bundle hashes and checks three author-defined EN/RU/AR versions of one guidance question. All return `context_only`, with no binding-rule citations; original English excerpts appear in `context_examples`. The questions exercise loading and non-binding treatment, not comprehensive evaluation or language review. These are global recommendations, **not UAE law or blanket classroom permission**. Read [integration notes](kb_candidates/unesco/INTEGRATION.md) and [required attribution/license notices](kb_candidates/unesco/THIRD_PARTY_NOTICES.md). The runner carries those notices in its output. The original eight bundle files and historical validation record are retained unchanged; their dated preparation status is not the current submission status.

## Recorded research results, not public-demo results
Original research corpus: 16 sources / 49 cards. Baseline external-model-authored adversarial set: **2/20 strict pass**. After targeted safety fixes on already exposed tests: **3/20 strict pass**, decision-only **9/20**. This is regression, NOT a fresh held-out estimate. Same-author dev 20/20 and old heldout 14/15 do not demonstrate generalization. Targeted safety regression 14/14; local pytest 26 passed / 1 skipped (reference-ingest compatibility not rerun). These aggregates were read from local artifacts; the source corpus is withheld pending redistribution review. Do not combine denominators or call this independent validation.

## Limitations
Curated missing-document matching is not comprehensive. RU/AR language output and glossary are not native-reviewed. LLM path is implemented but untested. No fine-tuning, sandbox deployment or production readiness is claimed. Three of twenty adversarial cases passing remains poor.

## Submission status
The organiser confirmed the submission address `aiforgoodlab@itu.int` and the cutoff of **10 November 2026, 23:59 UAE time (UTC+4)** in correspondence dated 10 November. That deadline was missed. A late cover email with the public repository reference was sent on **11 November at 11:47 UAE time**; receipt was acknowledged at **13:20 UAE time**. These correspondence facts do not establish admission to the competition, evaluation or acceptance. This repository update documents the reproducible public demonstration; it does not retroactively change those dates.

The requested package comprises a technical report of at most five pages, GitHub repository and policy/regulation/strategy knowledge base; a first-round demo video is optional (maximum seven minutes). **The default synthetic demo and three-card UNESCO context subset are not claimed to establish sufficient competition policy-KB coverage.** Real-source links are also supplied as a metadata index; the remaining research corpus and its redistribution review remain separate.
https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/

## Attribution and rights
`standards.py` contains a mapping derived from ITUAIReadiness commit 84010da9e9c443afcceeccb86d1700a662223395; its MIT notice is reproduced in THIRD_PARTY_NOTICES.md. Other original project code is published for inspection; no additional reuse license is granted yet. Original authors retain their rights.

## Anonymous evaluation presentation
Public results do not identify individual reviewing models or rank providers. Technical provider identifiers needed by optional adapters, search vocabulary, and legally required third-party attribution are retained; they are not endorsements. This repository is associated with its public GitHub owner and is not an anonymous account.
