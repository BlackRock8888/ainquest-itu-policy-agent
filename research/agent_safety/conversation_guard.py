"""Offline owner-side conversation guard sketch; no tools, blocking or execution.

Trusted host supplies canonical opaque IDs, verified corrections and receipts.
No transcript, private content or motive is stored. IDs/hashes can still be sensitive.
Authentication, durable state and correct source binding are outside this specimen.
"""
from dataclasses import dataclass
from enum import Enum
import re


def canonical(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", value):
        raise ValueError("canonical opaque ID required")


def refs(values):
    if type(values) is not tuple:
        raise ValueError("immutable evidence IDs required")
    for value in values:
        canonical(value)
    if len(set(values)) != len(values):
        raise ValueError("distinct evidence IDs required")


class ReceiptState(Enum):
    PROPOSED = "proposed"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass(frozen=True)
class Action:
    request_id: str
    action_id: str
    recipient_id: str
    payload_sha256: str

    def __post_init__(self):
        for value in (self.request_id, self.action_id, self.recipient_id):
            canonical(value)
        if not isinstance(self.payload_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.payload_sha256):
            raise ValueError("exact payload SHA256 required")


@dataclass(frozen=True)
class Receipt:
    action: Action
    state: ReceiptState

    def __post_init__(self):
        if not isinstance(self.action, Action) or not isinstance(self.state, ReceiptState):
            raise ValueError("typed action and receipt state required")


@dataclass(frozen=True)
class Correction:
    claim_id: str
    accepted_value_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        canonical(self.claim_id)
        canonical(self.accepted_value_id)
        refs(self.evidence_ids)
        if not self.evidence_ids:
            raise ValueError("verified correction needs evidence references")


@dataclass(frozen=True)
class Claim:
    claim_id: str
    value_id: str
    evidence_ids: tuple[str, ...] = ()
    quoted_or_hypothetical: bool = False

    def __post_init__(self):
        canonical(self.claim_id)
        canonical(self.value_id)
        refs(self.evidence_ids)
        if type(self.quoted_or_hypothetical) is not bool:
            raise ValueError("explicit context flag required")


@dataclass(frozen=True)
class PersuasionTurn:
    decision_id: str
    turn_id: str
    criterion_id: str
    evidence_ids: tuple[str, ...] = ()
    unanswered_objection_hypothesis: bool = False
    advocacy: bool = True

    def __post_init__(self):
        for value in (self.decision_id, self.turn_id, self.criterion_id):
            canonical(value)
        refs(self.evidence_ids)
        if type(self.unanswered_objection_hypothesis) is not bool or type(self.advocacy) is not bool:
            raise ValueError("explicit untrusted hypothesis flag required")


@dataclass(frozen=True)
class Identity:
    agent_id: str
    provider_id: str
    model_id: str
    role_id: str

    def __post_init__(self):
        for value in (self.agent_id, self.provider_id, self.model_id, self.role_id):
            canonical(value)


@dataclass(frozen=True)
class Result:
    status: str
    intervention: bool = False
    next_step: str = "none"
    indicators: tuple[str, ...] = ()


class ConversationGuard:
    """One instance per session. Only advisory statuses; NEVER permission to act.

    At most one intervention per key, with separate security/pressure budgets. The host must
    preserve the instance to enforce that bound. Disagreement is not a fault.
    Steps are suggestions to a host/user: they cannot initiate tools or messages.
    """
    def __init__(self, session_id, intervention_budget=3, *, pressure_budget=1):
        canonical(session_id)
        if any(type(x) is not int or x < 0 for x in (intervention_budget, pressure_budget)):
            raise ValueError("nonnegative integer intervention budget required")
        self.session_id = session_id
        self._remaining = {"security": intervention_budget, "pressure": pressure_budget}
        self._intervened = set()
        self._corrections = {}
        self._unmatched_evidence = {}
        self._turns = {}
        self._decision_evidence = {}
        self._criteria = {}
        self._host_identities = {}
        self._identity_corrections = set()

    def _result(self, status, key, next_step, indicators=(), *, budget="security"):
        intervene = key not in self._intervened and self._remaining[budget] > 0
        if intervene:
            self._intervened.add(key)
            self._remaining[budget] -= 1
        return Result(status, intervene, next_step if intervene else "none", indicators)

    def register_verified_correction(self, correction):
        """Only the trusted host's verification path may call this method."""
        if not isinstance(correction, Correction):
            raise ValueError("typed correction required")
        old = self._corrections.get(correction.claim_id)
        if old is not None and old != correction:
            raise ValueError("correction replacement needs external revalidation in a new case")
        self._corrections[correction.claim_id] = correction

    def check_claim(self, claim):
        if not isinstance(claim, Claim):
            raise ValueError("typed claim required")
        if claim.quoted_or_hypothetical:
            return Result("context_not_assertion")
        correction = self._corrections.get(claim.claim_id)
        if correction is None:
            return Result("no_verified_comparison")
        if claim.value_id == correction.accepted_value_id:
            return Result("consistent_with_correction")
        unmatched = set(claim.evidence_ids) - set(correction.evidence_ids)
        seen = self._unmatched_evidence.setdefault(claim.claim_id, set())
        new = unmatched - seen
        seen.update(unmatched)
        if new:
            return Result("new_evidence_needs_review")
        # Repetition does not verify evidence or resolve the original conflict.
        return self._result("conflicts_with_verified_correction", ("claim", claim.claim_id),
                            "show_correction_reference_once")

    def check_completion(self, action, receipt=None):
        """Call when completion is asserted; receipt comes from trusted execution host."""
        if not isinstance(action, Action) or (receipt is not None and not isinstance(receipt, Receipt)):
            raise ValueError("typed action and optional receipt required")
        if receipt is None:
            status = "receipt_absent"
        elif receipt.action != action:
            status = "receipt_mismatch"
        else:
            status = "receipt_" + receipt.state.value
        if status == "receipt_confirmed":
            return Result(status)
        return self._result(status, ("action", action.request_id), "verify_exact_receipt_before_next_step")

    def register_host_identity(self, identity):
        """Trusted transport/deployment binding ONLY, never infer from model self-labels."""
        if not isinstance(identity, Identity):
            raise ValueError("typed host identity required")
        old = self._host_identities.get(identity.agent_id)
        if old is not None and old != identity:
            raise ValueError("host identity change requires external revalidation/new case")
        self._host_identities[identity.agent_id] = identity

    def mark_verified_identity_correction(self, agent_id):
        """Host records correction delivered and verified against its own binding."""
        canonical(agent_id)
        if agent_id not in self._host_identities:
            raise ValueError("independent host binding required before correction")
        self._identity_corrections.add(agent_id)

    def check_self_identity(self, asserted_identity, *, actor_id):
        if not isinstance(asserted_identity, Identity):
            raise ValueError("typed self-identity required")
        canonical(actor_id)  # Transport-selected actor, NEVER the asserted agent ID.
        host = self._host_identities.get(actor_id)
        if host is None:
            return Result("identity_unknown_no_host_binding")
        if host == asserted_identity:
            return Result("identity_matches_host_binding")
        status = ("identity_mismatch_after_verified_correction"
                  if host.agent_id in self._identity_corrections else "identity_mismatch")
        return self._result(status, ("identity", host.agent_id), "show_host_identity_binding_once")

    def check_attribution(self, utterance_id, claimed_speaker_id, *, asserted_quote_sha256=None,
                          verified_speaker_id=None, verified_quote_sha256=None):
        """Host binds speaker and exact selected-quote bytes independently; no text stored.

        Both hashes must use the same host-defined exact-byte selection convention.
        Missing/malformed hashes are unverified, not evidence of misattribution.
        """
        canonical(utterance_id)
        canonical(claimed_speaker_id)
        valid_digest = lambda x: isinstance(x, str) and re.fullmatch(r"[0-9a-f]{64}", x)
        if (verified_speaker_id is None or not valid_digest(asserted_quote_sha256) or
                not valid_digest(verified_quote_sha256)):
            status = "attribution_unverified"
        else:
            canonical(verified_speaker_id)
            if (verified_speaker_id == claimed_speaker_id and
                    asserted_quote_sha256 == verified_quote_sha256):
                return Result("attribution_confirmed")
            status = "attribution_mismatch"
        return self._result(status, ("utterance", utterance_id), "check_source_attribution_once")

    def observe_turn(self, turn, *, actor_id):
        """actor_id is supplied by trusted transport, not the advocating model."""
        canonical(actor_id)
        if not isinstance(turn, PersuasionTurn):
            raise ValueError("typed turn required")
        delivery_key = (actor_id, turn.turn_id)
        old = self._turns.get(delivery_key)
        if old is not None:
            if old != turn:
                raise ValueError("turn ID cannot be overwritten")
            return Result("duplicate_delivery")
        self._turns[delivery_key] = turn
        if not turn.advocacy:
            return Result("non_advocacy_not_counted")
        case = (turn.decision_id, actor_id)
        seen = self._decision_evidence.setdefault(case, set())
        previous = self._criteria.get(case)
        indicators = []
        if previous is not None and not set(turn.evidence_ids) - seen:
            indicators.append("observed_no_new_evidence_ids")
        if previous is not None and previous != turn.criterion_id:
            indicators.append("observed_criterion_change_not_inherently_wrong")
        if turn.unanswered_objection_hypothesis:
            indicators.append("untrusted_unanswered_objection_hypothesis")
        seen.update(turn.evidence_ids)
        self._criteria[case] = turn.criterion_id
        if indicators and not any(i.startswith("observed_") for i in indicators):
            return Result("unverified_hypothesis_only", indicators=tuple(indicators))
        if "observed_no_new_evidence_ids" in indicators:
            return self._result("review_possible_pressure_not_motive", ("decision", *case),
                                "pause_optional_reversible_step_and_verify_one_criterion", tuple(indicators),
                                budget="pressure")
        if indicators:
            return Result("changed_criterion_advisory", indicators=tuple(indicators))
        return Result("no_indicator")


@dataclass(frozen=True)
class RepeatMeasurement:
    status: str
    count: int
    elapsed_ms: int  # Measured from correction; pre-correction observations report 0.


class RepeatCounter:
    """One host-bound case/value after verified correction, independent of interventions.

    Host provides session/case/correction identity and monotonic clock milliseconds.
    Counts identical contradicted assertions only, not quotations or provider metrics.
    The window starts strictly after correction and includes its end boundary.
    Late/out-of-order events are excluded.
    """
    def __init__(self, session_id, case_id, contradicted_value_id, correction_id,
                 *, corrected_at_ms, window_ms):
        for value in (session_id, case_id, contradicted_value_id, correction_id):
            canonical(value)
        if any(type(x) is not int or x < 0 for x in (corrected_at_ms, window_ms)):
            raise ValueError("explicit nonnegative integer clock and window required")
        self.session_id, self.case_id = session_id, case_id
        self.contradicted_value_id, self.correction_id = contradicted_value_id, correction_id
        self._start, self._window = corrected_at_ms, window_ms
        self._last, self._count, self._events = corrected_at_ms, 0, {}

    def observe(self, event_id, value_id, *, observed_at_ms, asserted=True):
        canonical(event_id)
        canonical(value_id)
        if type(observed_at_ms) is not int or observed_at_ms < 0 or type(asserted) is not bool:
            raise ValueError("explicit monotonic milliseconds and assertion flag required")
        event = (value_id, observed_at_ms, asserted)
        elapsed = max(0, observed_at_ms - self._start)
        old = self._events.get(event_id)
        if old is not None:
            if old != event:
                raise ValueError("event ID cannot change")
            return RepeatMeasurement("duplicate_delivery", self._count, elapsed)
        self._events[event_id] = event
        if observed_at_ms < self._start:
            status = "before_correction"
        elif observed_at_ms == self._start:
            status = "at_correction_time_excluded"
        elif observed_at_ms < self._last:
            status = "late_event_excluded"
        else:
            self._last = observed_at_ms
            if elapsed > self._window:
                status = "outside_window"
            elif not asserted or value_id != self.contradicted_value_id:
                status = "not_identical_contradicted_assertion"
            else:
                self._count += 1
                status = "counted"
        return RepeatMeasurement(status, self._count, elapsed)
