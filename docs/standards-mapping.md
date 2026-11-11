# Standards mapping and evidence boundary

This is the project's own implementation mapping, not an ITU certification, an assessment of legal compliance or a claim of competition acceptance. Node/dimension identifiers are retained from the reference recorded in `src/policy_agent/standards.py`: ITUAIReadiness commit `84010da9e9c443afcceeccb86d1700a662223395`. The required MIT attribution is in `THIRD_PARTY_NOTICES.md`.

## What a public reviewer can reproduce

The default corpus contains exactly one invented Demo University rule. It is marked `synthetic_test_only`; its source uses `example.invalid`. `kb/research-source-index.jsonl` has 16 real-source metadata entries, but the runtime does not ingest this index or download those documents. Separately, `kb_candidates/unesco/` contains three licensed global non-binding guidance excerpts loaded only by explicit path. This adds no binding UAE policy rule and does not restore the historical 49-card corpus.

| Pipeline node | Published implementation | Evidence and limitation |
| --- | --- | --- |
| SRC | `kb/` and separately `kb_candidates/unesco/kb/` | Default: one synthetic source/card. Explicit UNESCO subset: one source/three non-binding guidance cards. Real-source index is metadata only. |
| C | Local KB loading in `kb.py` | No public source collector or real-document ingestion workflow. The research collector is not included. |
| PP | `text.py`, `scope.py`, `kb/glossary.json` | Deterministic normalisation and EN/RU/AR term expansion; native language review pending. |
| M | `retrieve.py`, `evidence.py` | Lexical BM25 and evidence gate. Optional local model rephrasing exists in code but is not exercised in the reported validation. |
| P | Scope filters and curated missing-document rules | Demonstrated answer/refusal/clarification mechanics on synthetic inputs; not comprehensive policy conflict resolution. |
| D | `agent.py` answer objects | Citation identifiers, source metadata, unknowns and review flags. Synthetic labels remain visible in output. |
| SINK | `__main__.py`, `audit.py` | CLI/JSON and optional local logs; no production UI or hosted service. |
| MLFO | `replay.py` | One-agent stateful replay. A received syllabus is stored as context; its legal meaning is not parsed or validated. |
| Sandbox | `evaluate.py`, `evals/` | Local synthetic smoke/replay fixtures; no ITU sandbox or upstream ingestion execution is claimed. |

## AI Readiness dimensions

Dimension 4 is represented by scope fields. Dimension 6 by structured multilingual output. Dimension 9 by an explicit human-review flag. Dimension 10 by scope boundaries and documented unknowns. Dimension 11 by multilingual access mechanics. These are component mappings, not measured readiness scores. The dimension-7 claim concerning UAE strategy/charter cards belongs only to the withheld research corpus; those cards are absent from the public KB.

## Gaps

The reproducible public gap is the boundary between a runnable decision engine and auditable real-policy evidence: the public reviewer cannot reproduce historical research-corpus coverage or performance from the default synthetic demo or the separate three-card UNESCO guidance subset. Scope fields and refusal decisions provide a mechanism for recording uncertainty; they do not establish which law applies or that a source has formal approval.

Further research must verify source applicability, authority/approval, dates, exceptions and rights before adding real evidence. Any proposed standards or policy gap must cite the precise source/version and distinguish an implementation limitation, a knowledge-base omission and an actual gap in a policy or standard. This update makes no new factual claim that a UAE policy or ITU standard is missing.

## Assessment interpretation

`evals/synthetic-smoke.jsonl` is an author-defined six-case smoke assessment. `evals/scenarios/synthetic-progressive.json` is an author-defined eight-event replay. Expected labels are read by the evaluator after each agent result; they are excluded from inputs passed to `answer` and `Session.handle`. These examples were selected to exercise existing behaviour and provide no independent estimate of generalisation. Passing them must not be merged with the recorded research denominators in the README.
