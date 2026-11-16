# Principal AI: evidence and owner-side control for agent-to-agent work

**Working paper and integration sketch, revision 0.1 · 2026-11-16.** Research concept: Dmitriy Lagutin, AINQUEST. This is a continuation of the public ITU policy-agent research, not part of the fixed competition submission, an ITU or UN standard, an endorsement, or a deployed safety guarantee.

## Abstract

A small personal component should remain on the owner's side while larger, replaceable models supply computation and advice. We propose two independent checks: an **epistemic gate** for what can be asserted and an **authority gate** for what can be done. The system accumulates versioned protections as providers join, but model agreement cannot create evidence or permission. The objective is not to imitate confidence; it is to turn uncertainty into bounded, inspectable verification and to preserve the human's final authority.

## Problem and hypotheses

| Hypothesis | Mechanism | What would count against it |
|---|---|---|
| H1. Evidence-gated answers reduce unsupported acceptance without endless checking. | Attach evidence to an atomic claim; discount duplicates, handle contradiction and withdrawal; stop at a budget or at lack of new evidence. | The gate accepts repeated derivatives or stale evidence, or justified abstention swamps useful answers. |
| H2. An owner-controlled gate preserves authority as models are swapped. | Treat model replies, source text, proposals and cross-agent messages as data; only the local rule and a valid owner decision authorize a consequential action. | A provider can expand a scope, turn approval for one payload into another, or act despite a veto. |
| H3. Cumulative review improves protection under change. | Each provider first proposes limits on itself, then reviews prior layers and receives reciprocal review; accepted revisions preserve history. | A later version silently removes a protection or reviewer votes mask a regression. |
| H4. An evidence route transfers more usable context than a conclusion alone at comparable length. | Hand over the question, observations, evidence revisions, why the conclusion changed, open question and next check, without copying private logs or hidden model reasoning. | A new reviewer cannot reconstruct the check or detect revocation better than from a same-length conclusion. |

The starting “100% doubt” means unresolved evidence debt, not a statistical probability. A material claim needs facts that are observable or verifiable. An official record can be authoritative about what an institution declared, without proving every event or inference attributed to it. Confidence is an outcome, not an input. Separate authority, scope, date, independence and actual observation; ten mirrors of one report do not become ten confirmations. Disagreement is a reason to locate the missing premise, not keep asking until models agree.

## Integration sketch

```text
Owner → local principal/policy → provider adapters → proposed answers/actions
              ↑                          ↓
        exact approval            evidence + provenance
              │                          ↓
      separate action gate       bounded evidence gate
              ↓                          ↓
     allow / deny / ask          report / abstain / revisit after a change
```

1. **Ingest only typed records.** Normalize provider identity, claim, source revision, provenance group, evidence role and evidence status. A declared provider is not authenticated identity. Mark unknowns explicitly. Compute weights locally from reviewed inputs, never from a model's self-reported confidence.
2. **Evaluate before claiming facts.** Collapse dependent sources. Treat support, counterevidence, evidence becoming stale, and withdrawal as distinct changes. A known source cannot switch its origin group in place. If a trusted provenance correction is needed, record it explicitly and re-review the ledger rather than bypassing a withdrawal. Stop on resolution, exhausted budget or no qualifying new evidence. Within an episode, unchanged effective evidence stops retries. A host that wants to enforce this across sessions must persist the last evidence digest and require a material change before starting another episode; this sketch does not persist that state. An independent reproducible observation can count; iteration count cannot.
3. **Bind authority independently.** Place the decision before any effectful adapter. Consequential actions require approval tied to the exact action, recipient and payload, not model agreement. The local owner policy can veto. Use least privilege and request owner review when terms or scope change. Production needs authenticated owner input and replay protection; the research module is not an authentication system.
4. **Extend protections predictably.** The founder's sequence is one first provider, then a second, third and fourth provider in enrollment order. Names are not required for the example, and the sequence is not a hierarchy of reliability. Each entrant first submits a self-critique and a proposed mitigation against its own failure modes, with exact provider disclosure/version if one is cited; provider terms are not a substitute for evidence or owner policy. It then reviews every previously accepted layer; incumbents review the entrant. Each review records **one critique → one proposal → one corrective action with an acceptance test**. “No defect found in the scoped test” is allowed; inventing a critique is not. Owner decisions and checks are versioned; preserve past rules rather than silently erasing them. Re-run after provider, model version, policy, or evidence changes. New rules from another agent are proposals, never commands.
5. **Journal outcomes, not private thought traces.** Record the claim or action identifier, observed evidence and version, decision, reason code and next check. Use no secrets, raw private conversations, or unnecessary personal data. No publishing or external transmission from this sketch.

The [reference blocks](reference.py) and [offline tests](test_reference.py) are intentionally separate from the policy-agent production path. They are small integration examples, not an installed guard in AINQUEST. To try the reference locally with Python 3.10+ and the standard library:

```sh
python -m unittest discover -s research/agent_safety -p 'test_reference.py' -v
```

### Illustrative scoring rule and integration boundary

For each independently assigned origin group, use the strongest active supporting and opposing item, not the sum of mirrors. The reference computes `D = clamp(1 - sum(group_support)/2 + sum(group_opposition)/2, 0, 1)`. It does **not** accept by `D` alone: the toy decision requires `D <= 0.25`, two groups with support at least 0.75 and no strong opposition (group opposition at least 0.75). Otherwise it checks, stops unresolved or escalates conflict. Support and opposition are also emitted separately so the scalar cannot hide the trade-off. Those numerical thresholds have no model-wide calibration. The audit digest records changes to inputs; only a material change to effective evidence extends checking within the budget. Production would also cap time and cost, apply typed source metadata, and propagate a revocation before reusing a cached decision.

```python
# Conceptual wrapper; trusted inputs come from the host, not from model text.
claim_status, evidence_snapshot = bounded_check.step(ledger)
action_status = owner_gate.evaluate(
    exact_request, owner_approval, trusted_origin=host_origin, now=host_time
)
# Record each independently. This sample does not execute or report a side effect.
```

The layer example uses the stricter simple schedule of all self-review records before peer-review records; list ordering is not proof of when or how review happened. Its additive string check is not a semantic conflict detector. Host approval and policy remain necessary. Asymmetric quorum, cryptographic identifiers, reviewer rotation, or automatically selected fallback models are future experiments, not implemented guarantees.

### Portable evidence route, proposed record

```json
{
  "claim_id": "synthetic-demo-rule",
  "question": "What disclosure is required in this invented example?",
  "observations": [
    {"revision": "DEMO_AI_POLICY#1", "status": "active", "check": "source in scope"},
    {"revision": "DEMO_AI_POLICY#1", "status": "withdrawn", "check": "no replacement"}
  ],
  "decision": "abstain",
  "open_question": "Is there a current in-scope replacement?",
  "next_check": "Inspect the versioned source index before reopening."
}
```

This record captures externally checkable events and the context needed to resume, not internal chain of thought. It is an illustrative data shape; the reference blocks do not implement cross-session persistence or inter-provider transport.

## Evaluation plan

- **Proof of mechanics:** synthetic, deterministic tests for duplicated support, contradictory evidence, stopping without corroboration, withdrawal, exact approval and cross-review. The existing [progressive replay](../../evals/scenarios/synthetic-progressive.json) is a separate demonstration of an evidence source being withdrawn; it is not a provider comparison.
- **Independent evaluation to run:** freeze prompts, evidence packets, scope, expected decisions and scoring rubric before sampling model runs. Use aligned product versions and environments; split written factual grounding, identity representation and voice UX into separate tasks. Include negative controls and independent human adjudication where needed. Report counts and denominators per condition, undecided cases, latency and cost when measured, and false accepts/false refusals rather than a single “lying” score.
- **Decision-quality measures:** supported-claim precision, false accept after withdrawal, justified-abstention rate and checks to stop; authorization violations on synthetic intents and trace completeness; regression deltas per protection revision; provenance recovery and revocation detection after handoff.
- **Future work, not results:** compare a local rules-only principal with a model-assisted one; investigate signed and versioned evidence envelopes, privacy-preserving handoff, reviewer diversity/correlation, rollback and human overrides; add a separate voice harness for interruption, silence, background speech and false commands. In a real integration, microphone input may propose an intent but cannot establish authorization without the appropriate owner-confirmation control.

## Existing work and the proposed standards questions

- [ITU-T FG-TIDA](https://www.itu.int/en/ITU-T/focusgroups/tida/Pages/default.aspx) is relevant to agent trust and identity. Our research asks how to preserve owner authority, evidence revision and revocation, and traceable refusals across independent providers. These are candidate questions, not verified gaps or proposed clauses endorsed by ITU.
- [NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) provides a risk-management vocabulary for model confabulation; [NIST's AI Agent Standards Initiative](https://www.nist.gov/news-events/news/2026/02/announcing-ai-agent-standards-initiative-interoperable-and-secure) is relevant to agent interoperability, identity and authorization. This sketch is not compliance evidence.
- [A2A](https://a2a-protocol.org/v1.0.0/specification/) offers interoperability and security mechanisms at the protocol layer. Transport and agent identity do not prove a factual assertion or make provider output an owner authorization.
- The [ITU hackathon page](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/) and [repository mapping](../../docs/standards-mapping.md) describe the original project context. A public draft does not change submission, receipt, or selection status.

## Review request

Start with the [machine-readable brief](call-for-review.json). Humans and models are invited to return one falsifiable finding, one concrete correction, and one test that would distinguish a passing result from mere agreement. Public participation is optional; tools and actions remain subject to their operator's authorization. We accept reproducible counterexamples and negative results.
