"""Offline research sketch, NOT a security boundary or calibrated truth estimator.

Trusted adapters must authenticate sources, owners and reviewers outside this module.
Models cannot supply those trusted assertions. No tool/network/action executes here.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite


@dataclass(frozen=True)
class Evidence:
    source_id: str
    origin_group: str  # Mirrors/syndication share an independently assigned group.
    revision: int
    support: float  # 0..1 heuristic strength, not probability.
    oppose: float = 0.0
    active: bool = True

    def __post_init__(self):
        if (not isinstance(self.source_id, str) or not self.source_id.strip() or
                not isinstance(self.origin_group, str) or not self.origin_group.strip() or
                type(self.revision) is not int or self.revision < 1):
            raise ValueError("source, provenance and positive revision required")
        if any(type(x) not in (int, float) or not isfinite(x) or not 0 <= x <= 1
               for x in (self.support, self.oppose)):
            raise ValueError("strength must be finite and in [0,1]")


class EvidenceLedger:
    """One claim per ledger. A source update replaces its older revision."""
    def __init__(self):
        self.records = {}
        self.withdrawn_groups = set()

    def withdraw_origin(self, origin_group):
        """Trusted source-withdrawal event invalidates every mirror in that group.

        Reinstatement is deliberately unsupported here; rebuild/review separately.
        """
        if not origin_group:
            raise ValueError("origin required")
        self.withdrawn_groups.add(origin_group)

    def ingest(self, item: Evidence):
        old = self.records.get(item.source_id)
        if old and item.revision <= old.revision:
            raise ValueError("stale or duplicate source revision")
        if old and item.origin_group != old.origin_group:
            raise ValueError("source provenance is sticky; reclassification requires external review")
        self.records[item.source_id] = item

    def snapshot(self):
        groups = {}
        for e in self.records.values():
            if e.active and e.origin_group not in self.withdrawn_groups:
                s, o = groups.get(e.origin_group, (0.0, 0.0))
                groups[e.origin_group] = (max(s, e.support), max(o, e.oppose))
        support = sum(s for s, _ in groups.values())
        opposition = sum(o for _, o in groups.values())
        # Toy policy: two strong independent origins, contradiction veto, D <= .25.
        corroborators = sum(s >= .75 and o < .75 for s, o in groups.values())
        conflict = any(o >= .75 for _, o in groups.values())
        # A bounded display index: this is NOT P(false) or scientific confidence.
        doubt_index = max(0.0, min(1.0, 1.0 - support / 2.0 + opposition / 2.0))
        payload = [(e.source_id, e.origin_group, e.revision, e.support,
                    e.oppose, e.active) for e in sorted(self.records.values(),
                                                     key=lambda x: x.source_id)]
        digest = sha256(json.dumps([payload, sorted(self.withdrawn_groups)],
                                  separators=(",", ":")).encode()).hexdigest()
        # Only effective group strengths advance the check, not mirror count,
        # source revision metadata or zero-weight records. Normalize numeric types.
        effective = [(g, float(s), float(o)) for g, (s, o) in sorted(groups.items())
                     if s or o]
        effective_digest = sha256(json.dumps(effective, separators=(",", ":"))
                                  .encode()).hexdigest()
        return {"digest": digest, "raw_digest": digest,  # digest is audit-only alias.
                "effective_digest": effective_digest, "doubt_index": doubt_index,
                "support_strength": support, "opposition_strength": opposition,
                "corroborators": corroborators, "conflict": conflict,
                "qualified": corroborators >= 2 and not conflict and doubt_index <= .25}


class BoundedCheck:
    """Call once per observation round; recompute after source withdrawal.

    A terminal result ends this episode. A newly changed source starts a NEW episode;
    never reuse an old acceptance without recomputing the current ledger.
    """
    def __init__(self, max_rounds=3):
        if type(max_rounds) is not int or max_rounds < 1:
            raise ValueError("positive integer budget required")
        self.max_rounds, self.rounds, self.previous, self.terminal = max_rounds, 0, None, None

    def step(self, ledger):
        if self.terminal:
            raise ValueError("episode finished; revalidate with a new episode")
        self.rounds += 1
        s = ledger.snapshot()
        if s["conflict"]:
            result = "escalate_conflict"
        elif s["qualified"]:
            result = "accept_provisionally"
        elif self.rounds >= self.max_rounds or s["effective_digest"] == self.previous:
            result = "stop_unknown"
        else:
            result = "check_more"
        self.previous = s["effective_digest"]
        if result != "check_more":
            self.terminal = result
        return result, s


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    action: str
    recipient: str
    payload_sha256: str


@dataclass(frozen=True)
class Approval:
    """Created ONLY by authenticated owner UI, never deserialized from model output."""
    request: ActionRequest
    expires_at: int


class OwnerGate:
    """Local deny-by-default sketch. Caller policy is trusted; grant cannot expand it.

    Authentication, secure clock, concurrent/atomic storage and execution receipts are
    outside scope. In production, bind this to actual bytes and an authenticated UI.
    Every permitted action needs approval here, deliberately stricter than many apps.
    """
    def __init__(self, allowed_actions):
        if isinstance(allowed_actions, (str, bytes)):
            raise ValueError("allowlist must be a collection of action names, not a string")
        self.allowed_actions = frozenset(allowed_actions)
        self.used = set()

    def evaluate(self, request, approval, *, trusted_origin, now):
        if trusted_origin != "authenticated_owner_ui":
            return "deny_untrusted_approval"
        if request.action not in self.allowed_actions:
            return "deny_policy"
        if type(now) is not int or now < 0:
            return "deny_clock"
        if not request.request_id or request.request_id in self.used:
            return "deny_replay"
        if (approval is None or type(approval.expires_at) is not int or
                approval.request != request or now >= approval.expires_at or not request.recipient):
            return "deny_scope_or_expiry"
        if (not isinstance(request.payload_sha256, str) or len(request.payload_sha256) != 64 or
                any(c not in "0123456789abcdef" for c in request.payload_sha256)):
            return "deny_payload_digest"
        self.used.add(request.request_id)
        return "permitted_once"  # An authorization decision, NOT an execution receipt.


@dataclass(frozen=True)
class Layer:
    participant: str  # Canonical ID: nonblank, casefolded, no outer whitespace.
    version: int
    rules: tuple[str, ...]


@dataclass(frozen=True)
class Review:
    reviewer: str
    subject: str
    candidate_digest: str
    critique: str
    proposal: str
    correction: str  # One concrete resolution; can be justified no-change.
    acceptance_test: str  # Proposed check, NOT independently observed evidence.
    passed: bool  # Reviewer assertion, not a verified test execution receipt.


def candidate_digest(layers):
    payload = [(x.participant, x.version, x.rules) for x in layers]
    return sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def admit_layers(previous, candidate, reviews, *, owner_approved_digest):
    """Return a new tuple, never mutate prior layers. Order follows owner enrollment.

    Reviews are bounded N*N records: ALL self-reviews precede ALL peer reviews.
    Authenticated reviewer identity and substantive correctness are NOT proved here.
    Consensus is not evidence of truth. Layers do not create or expand permissions.
    """
    previous, candidate = tuple(previous), tuple(candidate)
    members = [x.participant for x in candidate]
    if (not members or any(not isinstance(x, str) or not x or
                           x != x.strip().casefold() for x in members) or
            len(set(members)) != len(members)):
        raise ValueError("unique canonical participant IDs required")
    if members[:len(previous)] != [x.participant for x in previous]:
        raise ValueError("cannot remove/reorder existing participants")
    for i, layer in enumerate(candidate):
        if (type(layer.version) is not int or layer.version < 1 or
                type(layer.rules) is not tuple or not layer.rules or
                any(not isinstance(r, str) or not r.strip() for r in layer.rules)):
            raise ValueError("positive version and nonempty rules required")
        if i < len(previous):
            old = previous[i]
            if layer != old and (layer.version <= old.version or not set(old.rules) <= set(layer.rules)):
                raise ValueError("change needs newer version and retained prior rules")
    digest = candidate_digest(candidate)
    if owner_approved_digest != digest:
        raise ValueError("owner approval must bind exact candidate")
    expected = {(a, b) for a in members for b in members}
    seen = set()
    self_reviews = {(a, a) for a in members}
    for r in reviews:
        key = (r.reviewer, r.subject)
        if r.reviewer != r.subject and not self_reviews <= seen:
            raise ValueError("all self-reviews must precede peer reviews")
        if (key not in expected or key in seen or r.candidate_digest != digest or
                r.passed is not True or not all(isinstance(x, str) and x.strip() for x in
                    (r.critique, r.proposal, r.correction, r.acceptance_test))):
            raise ValueError("missing, duplicate, stale or unresolved review")
        seen.add(key)
    if seen != expected:
        raise ValueError("self and reciprocal cross-reviews required")
    return candidate
