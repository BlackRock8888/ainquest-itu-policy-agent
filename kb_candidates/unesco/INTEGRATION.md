# Explicit integration of the recovered UNESCO subset

The eight recovered files, including their README, attribution, historical VALIDATION.json and MANIFEST_SHA256.json, are retained byte-for-byte. Their descriptions of unpublished status and the 22 historical checks describe preparation on 9 November 2026; they are not current submission status or a claim that those 22 checks were rerun here. Current repository status is in the root README. Current verification is in the root VALIDATION.md.

This separately licensed subset has one source and three English UNESCO guidance cards. All three are `global_nonbinding`; none is a binding UAE rule. The independent-conversation context of the age recommendation remains in the original quote and annotation. The default `kb/` remains the one-card synthetic demo. There is no automatic merging and no change to the evidence gate.

From the repository root:

```sh
python scripts/check_unesco_candidate.py
```

The runner uses the existing `load_kb(custom_path)` interface, verifies the recovered manifest and corpus hash, and asks three author-defined EN/RU/AR versions of one age-guidance question. Expected behaviour is `context_only`, no binding-rule citations and original-language UNESCO excerpts in `context_examples`. The runner includes page/context/attribution fields and the full bundled notices alongside its JSON answer output. The compact core agent citation format does not carry all reuse notices itself.

The historical 22 checks, original 49-card corpus and reported research metrics are separate. This three-question check is not independent validation, a language-quality test, a legal interpretation or comprehensive policy-KB coverage. Reuse and adaptations must retain the attribution, license and required notices in THIRD_PARTY_NOTICES.md; the dataset license does not grant a license to unrelated project code.
