# External conversation guard: verification without endless debate

**Independent research sketch · 2026-11-16.** This extends the [previous working paper](README.md), not the fixed competition package. It is not a standards-body recommendation, a deployed safety layer or a lie detector.

## What exists and what this adds

The evidence reference already groups dependent sources, bounds checking and handles withdrawal. The owner gate validates scope and exact approval; the [source snapshot specimen](source-snapshots.md) preserves key observations and decision history. Those mechanisms did not by themselves check a conversation for a superseded assertion repeatedly presented as current, a success statement without a matching receipt, or an attribution without an exact source anchor.

This sketch adds a small checker outside the generating model. Its input is structured host events, not free-form interpretation of motives. It reports observable mismatches. Disagreement cannot, by itself, supply evidence, prove someone lied, or establish which participant is more capable.

## Observable checks

| Case | What the host can check | Guard interpretation |
|---|---|---|
| Repeated claim after a recorded correction | Same claim identity and superseded value in the same session; distinguish new evidence and a quotation from an assertion. | Ask for the new evidence or mark the old assertion unresolved. Repetition does not make it true. |
| Continued persuasion without progress | Repeated advocacy by the same host-bound actor on the same decision without new evidence. Criterion changes and an objection hypothesis can be recorded, but alone do not cause an interruption. | Stop the debate budget, name the missing fact or route to review. A strong tone alone is not a signal. Neither is an unverified objection on its own grounds for an interruption. |
| Self-identity after a correction | Host-selected actor identity from the authenticated session or configured adapter, not the actor identifier in model text. | Missing independent binding means unknown; a persistent mismatch supports testing or restricting that actor, not a conclusion about intent. |
| Action reported complete | Exact request identity, scope and outcome from a trusted executor; proposed, requested, pending and completed are different states. | No valid matching success receipt means “completion not confirmed,” not “the agent deliberately lied.” |
| Words attributed to someone | Trusted speaker reference plus a digest of the exact selected words; paraphrases must be explicitly presented as paraphrases. | If the receipt is absent or mismatched, label the attribution unverified. Do not invent words or store full conversations. |

The [offline reference](conversation_guard.py) and [synthetic tests](test_conversation_guard.py) exercise typed inputs supplied by a trusted host. They do not extract claims from text, verify speaker identity, call a model, send a message or execute an action. Audit only minimal identifiers and controlled reason codes. The guard can miss distortions or flag harmless cases. An observed mismatch is not sufficient evidence of deliberate fabrication; the caller may have supplied incomplete or mislabeled data. Keep an exception for genuine new evidence and distinguish restating an old claim for analysis from asserting it as true.

## Limited intervention and small steps

The guard should interrupt only for a material change: an unsupported completion, contradiction with a recorded correction, exposure outside an allowed scope, or a conversation that is no longer gathering information. Measure repeated contradictory assertions only within a named session and window after a verified correction, with distinct event IDs and an externally observed clock. Do not report this as a provider-wide error rate. Record a reason, a bound on interventions per case and session, and separate a pressure budget from the reserve for identity, attribution and receipts; do not indefinitely ask a person or a model the same question. In a real application, routine steps inside a standing, narrowly scoped permission can proceed without repeatedly interrupting the owner. Read-only or reversible first steps are useful when genuinely low risk; they do not grant authority for later steps. Any new recipient, expanded permissions, or consequential action still goes through the existing owner gate. The external rule does not control a proprietary model's internal behavior. Its suggested pause or removal from an action role must be applied by a separate host under the owner's rules; no permissions are altered by the sample.

```text
model output → host evidence and receipts → local guard → one bounded finding
                                        → owner gate → separately authorized tool
```

## Evaluation plan

```sh
python -m unittest discover -s research/agent_safety -p 'test_conversation_guard.py' -v
```

The initial isolation tests are synthetic. For a later independent study, freeze the transcripts or typed events, annotations, evidence IDs and expected outcome before testing. Compare false escalation on genuine disagreement or quoted corrections, unsupported completion detection, attribution accuracy, loops stopped, and unnecessary interventions. Separate integrity of the host's records from the guard's behavior. The research goal is fewer avoidable verification loops without increased false acceptance, not higher agreement or an inferred deception score.

A proposed first experiment is 20 frozen synthetic sessions with an independently checked correction at turn N, a later attempted repeat, and genuine objections or quotations as controls. Compare the same model or fixture with and without the external journal and score repeat rates, false interruptions and missed unsupported actions. This experiment has not been run.
