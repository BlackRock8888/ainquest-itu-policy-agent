# Public demonstration validation

## Version and scope

This delivery is based on public repository commit `476531ace392fb7867e6d1231461ce11fbe43f1f` (9 November 2026). The original downloaded source snapshot was preserved separately. This file records the local follow-up validation; it does not assert that these changes have already been pushed or accepted by ITU.

Validation execution recorded by the evaluator at `2026-11-11T23:45:28+00:00` (UTC); replay at `2026-11-11T23:45:28+00:00`.

Runtime: Python 3.12.14, standard library only. The initial default-demo checks used no model, external API, credential, sandbox deployment or real-policy corpus. Pytest was not installed or run in this environment. The dependency-free runner executes the actual test functions in `tests/test_demo.py` and `tests/test_export.py` and propagates assertion failures. A separate later check of the recovered UNESCO subset is recorded below.

Default corpus: one invented source and one invented rule. SHA-256 of `kb/cards.jsonl`:

```text
3e8ae880d5e79285be5890c0fc3e15e94e7cb70f2d92196eee27606994e63081
```

This matches `kb/CORPUS_SHA256`. The real-source index contains 16 metadata records and is not loaded as answer evidence. The default `kb/` source/card files and glossary were not changed by this delivery.

## Reproduce from the repository root

```sh
python scripts/check_public_demo.py
PYTHONPATH=src python -m policy_agent eval evals/synthetic-smoke.jsonl --out runs/synthetic-smoke.json
PYTHONPATH=src python -m policy_agent replay evals/scenarios/synthetic-progressive.json --out runs/synthetic-replay.json
PYTHONPATH=src python -m policy_agent standards
PYTHONPATH=src python -m policy_agent export-upstream runs/synthetic-export
```

| Check | Observed result |
| --- | --- |
| Original smoke functions | 2/2 passed: synthetic disclosure citation and missing-university-policy refusal. |
| Export regression | 1/1 passed: missing optional binding evidence no longer crashes; synthetic label, no-authority fallback, source URL and corpus hash are preserved. |
| Six-case synthetic assessment | 6/6 expected outcomes; decision and citation checks passed for all six cases. |
| Language consistency example | One author-defined EN/RU/AR group produced the same decision and cited source; this is not a language-quality validation. |
| Eight-event progressive replay | 8/8 expected event checks passed. |
| Standards output | Valid JSON; nine pipeline nodes and six dimension descriptions. |
| Export command | Exit code 0; one synthetic text file and manifest written. Actual upstream ingestion was not run. |

All five commands returned exit code 0. JSON assessment/replay outputs are generated under `runs/`, which is ignored by Git. Run IDs, timestamps and latency vary; expected decisions/citation identifiers and the corpus hash are stable for these fixtures.

## Demonstrated sequence

The replay records incomplete input, answers an English synthetic disclosure question, receives a synthetic syllabus, carries the institution scope into Russian and Arabic questions, refuses an unsupported detector allegation, withdraws the only card and refuses to reuse it. Receipt of the syllabus demonstrates context storage, not interpretation of a real course rule. The detector example has no supporting detector-policy card and therefore refuses.

## Reproduced defect and minimal correction

On the unchanged base source, `export(load_kb(), temporary_output_directory)` raised `KeyError('binding_evidence')` because that optional field is absent from the published synthetic source. The fix reads the optional field with a fallback of `not supplied; no authority inferred`. The regression checks the exported content and manifest. No source authority, real policy text or new knowledge was added.

## Interpretation limits

The six assessment cases and eight replay events were authored for this demonstration after reading the implementation. Passing them proves only that these selected mechanics execute as expected. They are not held-out tests, independent validation, real-policy coverage or an accuracy estimate. Do not combine these counts with the historical research metrics in README. The optional model path and language quality remain unvalidated. The exported path retains the existing upstream naming convention; the content remains explicitly synthetic and does not demonstrate an authentic UAE policy submission or upstream compatibility.

## Separate UNESCO subset integration check

Run at `2026-11-11T23:47:59+00:00` with Python 3.12.14, no model or network. Command:

```sh
python scripts/check_unesco_candidate.py
```

Observed: **3/3 author-defined EN/RU/AR examples returned `context_only`**, with an empty binding-rule `citations` list. Each cited `UNESCO_GENAI_GUIDANCE_2023#1` and `#3` in `context_examples`; original English quotations matched their loaded cards byte-for-byte. The runner preserves original page/context fields and includes the complete UNESCO attribution/license notices in its JSON output. This is one question in three languages, not three independent use cases or language-quality validation.

The existing `load_kb(custom_path)` loaded one source and three `global_nonbinding` cards without changing the evidence gate or default KB. All seven entries in the recovered manifest matched; the eight original bundle files were copied unchanged. Corpus SHA-256: `522884b96240e02d3a062ab631c73be845d0bf0bbe1fe61aa6765f920d598105`. The historical candidate `VALIDATION.json` reports 22 checks dated 9 November; those 22 checks were **not rerun** here and are not merged with this result. The full 49-card research corpus remains unavailable in this public package.

The default `kb/cards.jsonl` hash still matches `3e8ae880d5e79285be5890c0fc3e15e94e7cb70f2d92196eee27606994e63081`. The separate dataset is global guidance, not binding UAE policy or blanket classroom permission. See `kb_candidates/unesco/INTEGRATION.md` and the preserved notices before redistributing outputs.
