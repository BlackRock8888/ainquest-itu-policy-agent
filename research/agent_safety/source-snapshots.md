# Source snapshots: remember what the evidence said when we used it

**Working paper extension 0.1 · 2026-11-16.** Research concept: Dmitriy Lagutin, AINQUEST. A URL in a decision trail is not enough: the page can change, disappear, or later report a different creation date. Record a small versioned observation alongside the route to the decision, not an archive of every page.

## Observation contract

| Field | Meaning |
|---|---|
| Source identifier and locator | Stable source identifier, canonical URL if available, and precise anchor such as a section, table row, footnote or page. |
| Creation/publication as reported at observation | When the source says it was created or published, including wording or date precision when available. Unknown stays unknown. A page's updated date and an HTTP timestamp are not substitutes. |
| First seen, observed at, last seen | Times when this system actually read the source. Record the observation time with a UTC offset; derive first and last from the log. They are not facts about when the source was written. |
| Version and selected-content fingerprint | Publisher revision, if known; a fingerprint of selected anchors and relevant metadata for comparison. It cannot prove all other page content was unchanged, nor prove authorship. A distinct fact fingerprint ignores tags, row order and locator-only edits, so formatting does not count as new evidence. |
| Fact anchors | Minimal selected facts, exact values and units, short terms or subject tags, and a locator. Also distinguish an event date or effective-as-of date from when the source was created or accessed. |
| Decision lineage | A versioned observation does not itself update a conclusion. Each stable claim ID can have one root. A changed conclusion must extend that claim’s current revision, identify the newly observed evidence and record the reason. Both versions are retained. A changed publisher date counts toward a changed conclusion only when captured as a material fact in its own right, not merely as amended catalog metadata. |

### Three examples

1. **Menu:** `dessert.price=34 AED`, tag `menu`, effective date `2026-11-16`, locator `Desserts › Apple tart`. A later observation may say 39 AED. The earlier 34 AED is what we saw, not a claim that the current price is 34 AED.
2. **Historical event:** Keep the event date asserted by the source, the publication date when available, and the historical claim's locator. A publication date alone cannot resolve competing event dates.
3. **Definition:** Save the term, scope or jurisdiction, edition, section number and the minimum needed paraphrase or permitted excerpt. A new edition may change the definition; the original conclusion still points to the earlier passage. A moved section or a new tag alone is not a substantive change.

All examples are synthetic. Do not publish full menus, private chats or raw payloads. Store only what is necessary and authorized; a digest is an integrity aid, not a permission decision or an independent fact.

## Integration and evaluation

Use [the reference blocks](source_snapshots.py) and [their tests](test_source_snapshots.py). The host selects the minimal anchors, records other evidence separately from a source's self-description, and decides whether it can retain or disclose each field. The host supplies canonical claim/source IDs and a credible clock; the specimen rejects a second root or a stale or cross-claim parent. The fingerprint checks changes in selected fields, not semantic relevance, truth, equivalence or independence. An unrelated new caption is not sufficient reason to change a claim in a real system. This offline specimen does not fetch a page, verify an external timestamp, authenticate a source, persist a shared journal or automatically change a decision.

```text
source observation → selected fact anchors → observation digest
         │                     │
claimed dates ≠ access dates   └→ decision v1 → new evidence + reason → decision v2
```

Run the isolated tests with the Python standard library:

```sh
python -m unittest discover -s research/agent_safety -p 'test_source_snapshots.py' -v
```

**Hypothesis to test:** At equal storage budgets, a later reviewer using a recorded observation plus its evidence route can reconstruct what was known and detect changed evidence more reliably than with a URL and conclusion alone. Compare citation recovery, detection of a changed anchor, false change alerts, retention footprint and intentional abstention. Test same content viewed twice, changed content at the same URL, publisher date corrections, and an unknown timestamp. No measured improvement is claimed yet.
