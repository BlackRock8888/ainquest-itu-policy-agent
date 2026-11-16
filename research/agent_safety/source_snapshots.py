"""Offline selected-observation sketch; no fetcher, full archive, actions or permissions.

A trusted host supplies source identity, read IDs and actual observation timestamps.
Source-reported dates and captions are recorded claims, not verified facts. Digests
cover only the selected brief, never prove completeness or original-page integrity.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def optional_text(value):
    return value is None or nonblank(value)


@dataclass(frozen=True)
class Caption:
    """Ordered selected assertion, with verbatim value/unit when relevant.

    Strings preserve exact decimals, dates, currency and formatting, not arithmetic.
    Locator identifies where the selection was observed, not an external instruction.
    """
    fact: str
    locator: str
    tags: tuple[str, ...] = ()
    exact_value: str | None = None
    unit: str | None = None
    effective_or_event_date_raw: str | None = None

    def __post_init__(self):
        if not nonblank(self.fact) or not nonblank(self.locator):
            raise ValueError("fact and evidence locator required")
        if type(self.tags) is not tuple or any(not nonblank(x) for x in self.tags):
            raise ValueError("immutable text tags required")
        if any(not optional_text(x) for x in (self.exact_value, self.unit,
                                               self.effective_or_event_date_raw)):
            raise ValueError("value and unit must be exact strings or unknown")
        if self.unit is not None and self.exact_value is None:
            raise ValueError("unit requires a value")


@dataclass(frozen=True)
class Observation:
    read_id: str
    source_id: str
    observed_at: datetime
    captions: tuple[Caption, ...]
    source_created_raw: str | None = None
    source_published_raw: str | None = None
    external_revision: str | None = None

    def __post_init__(self):
        if not nonblank(self.read_id) or not nonblank(self.source_id):
            raise ValueError("read and source identity required")
        if (not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None or
                self.observed_at.utcoffset() is None):
            raise ValueError("timezone-aware observation time required")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(timezone.utc))
        if (type(self.captions) is not tuple or not self.captions or
                any(not isinstance(x, Caption) for x in self.captions)):
            raise ValueError("nonempty immutable ordered captions required")
        if any(not optional_text(x) for x in (self.source_created_raw,
                                             self.source_published_raw, self.external_revision)):
            raise ValueError("source metadata must be raw strings or unknown")

    @property
    def brief_digest(self):
        # Deliberately excludes read/access time, IDs and external revision labels.
        # A changed revision label alone is not new selected factual content.
        payload = {"created_raw": self.source_created_raw,
                   "published_raw": self.source_published_raw,
                   "captions": [(c.fact, c.locator, c.tags, c.exact_value, c.unit,
                                 c.effective_or_event_date_raw)
                                for c in self.captions]}
        return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")).encode("utf-8")).hexdigest()

    @property
    def fact_digest(self):
        # Ignore presentation, duplicate captions and source metadata relabeling.
        # Source dates affect this digest only if explicitly selected as a fact.
        # Textual novelty remains a heuristic, not semantic truth verification.
        facts = {json.dumps((c.fact, c.exact_value, c.unit, c.effective_or_event_date_raw),
                            ensure_ascii=False, separators=(",", ":")) for c in self.captions}
        return sha256(json.dumps(sorted(facts), ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8")).hexdigest()

    @property
    def evidence_key(self):
        return self.source_id, self.fact_digest


@dataclass(frozen=True)
class DecisionRevision:
    claim_id: str  # Stable identity supplied by trusted host, not model text.
    revision_id: str
    parent_id: str | None
    statement: str
    change_reason: str
    evidence_reads: tuple[str, ...]


class SnapshotMemory:
    """Append-only in-memory specimen, not durable storage or an authenticity service.

    Distinct read IDs are trusted host receipts; identical repeat delivery is idempotent.
    first_seen/last_seen use event timestamps, not arrival order or source date claims.
    Revisions are proposed knowledge records only: no approval, actions or source edits.
    """
    def __init__(self):
        self._reads = {}
        self._decisions = {}
        self._heads = {}

    def record(self, observation):
        if not isinstance(observation, Observation):
            raise ValueError("validated observation required")
        old = self._reads.get(observation.read_id)
        if old is not None and old != observation:
            raise ValueError("read ID cannot overwrite an earlier observation")
        self._reads[observation.read_id] = observation
        return observation

    def get(self, read_id):
        return self._reads[read_id]

    def source_history(self, source_id):
        return tuple(sorted((x for x in self._reads.values() if x.source_id == source_id),
                            key=lambda x: (x.observed_at, x.read_id)))

    def access_bounds(self, source_id):
        history = self.source_history(source_id)
        if not history:
            raise ValueError("source has not been observed")
        return history[0].observed_at, history[-1].observed_at

    def revise(self, revision_id, statement, change_reason, evidence_reads, *, claim_id, parent_id=None):
        if not nonblank(claim_id) or claim_id != claim_id.strip():
            raise ValueError("stable nonblank claim ID without outer whitespace required")
        if claim_id in self._heads:
            if parent_id != self._heads[claim_id]:
                raise ValueError("revision must extend this claim's current head")
        elif parent_id is not None:
            raise ValueError("new claim requires its own root, not another claim's parent")
        if any(not nonblank(x) for x in (revision_id, statement, change_reason)):
            raise ValueError("revision ID, statement and change reason required")
        if revision_id in self._decisions:
            raise ValueError("decision revision cannot be overwritten")
        if (type(evidence_reads) is not tuple or not evidence_reads or
                any(not nonblank(x) for x in evidence_reads) or
                len(set(evidence_reads)) != len(evidence_reads) or
                any(x not in self._reads for x in evidence_reads)):
            raise ValueError("distinct recorded evidence read IDs required")
        new_keys = {self._reads[x].evidence_key for x in evidence_reads}
        if parent_id is not None:
            if parent_id not in self._decisions:
                raise ValueError("known parent revision required")
            latest_by_source = {}
            ancestor_times = []
            cursor = parent_id
            while cursor is not None:
                previous = self._decisions[cursor]
                for read_id in previous.evidence_reads:
                    observation = self._reads[read_id]
                    old = latest_by_source.get(observation.source_id)
                    if old is None or observation.observed_at > old.observed_at:
                        latest_by_source[observation.source_id] = observation
                ancestor_times.extend(self._reads[x].observed_at for x in previous.evidence_reads)
                cursor = previous.parent_id
            prior_keys = {x.evidence_key for x in latest_by_source.values()}
            if not any(self._reads[x].evidence_key not in prior_keys and
                       self._reads[x].observed_at > max(ancestor_times) for x in evidence_reads):
                raise ValueError("revision needs later-observed new source evidence or changed selected content")
        revision = DecisionRevision(claim_id, revision_id, parent_id, statement, change_reason, evidence_reads)
        self._decisions[revision_id] = revision
        self._heads[claim_id] = revision_id
        return revision

    def decision(self, revision_id):
        return self._decisions[revision_id]
