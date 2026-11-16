"""Synthetic IDs only; no inference about model/provider motives."""
from dataclasses import replace
import unittest
from conversation_guard import (Action, Receipt, ReceiptState, Correction, Claim,
                                PersuasionTurn, Identity, ConversationGuard, RepeatCounter)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = ConversationGuard("session-1", 10)
        self.action = Action("request-1", "small-step", "target-1", "a" * 64)

    def test_exact_receipt_states(self):
        self.assertEqual(self.guard.check_completion(self.action).status, "receipt_absent")
        for state in ReceiptState:
            result = self.guard.check_completion(self.action, Receipt(self.action, state))
            self.assertEqual(result.status, "receipt_" + state.value)
        self.assertFalse(result.intervention)

    def test_completion_receipt_binds_all_fields(self):
        for field, value in (("request_id", "request-2"), ("action_id", "other"),
                             ("recipient_id", "target-2"), ("payload_sha256", "b" * 64)):
            receipt = Receipt(replace(self.action, **{field: value}), ReceiptState.CONFIRMED)
            self.assertEqual(self.guard.check_completion(self.action, receipt).status, "receipt_mismatch")
        self.assertEqual(self.guard.check_completion(self.action, Receipt(self.action, ReceiptState.CONFIRMED)).status,
                         "receipt_confirmed")

    def test_correction_replay_context_new_evidence(self):
        self.guard.register_verified_correction(Correction("claim-1", "corrected", ("e1",)))
        claim = Claim("claim-1", "different", ("e1",))
        self.assertTrue(self.guard.check_claim(claim).intervention)
        self.assertFalse(self.guard.check_claim(claim).intervention)
        self.assertEqual(self.guard.check_claim(replace(claim, quoted_or_hypothetical=True)).status,
                         "context_not_assertion")
        self.assertEqual(self.guard.check_claim(replace(claim, evidence_ids=("e2",))).status,
                         "new_evidence_needs_review")
        self.assertEqual(self.guard.check_claim(replace(claim, value_id="corrected")).status,
                         "consistent_with_correction")

    def test_disagreement_without_comparison_is_not_fault(self):
        self.assertEqual(self.guard.check_claim(Claim("claim-2", "disagree")).status,
                         "no_verified_comparison")

    def test_correction_cannot_silently_change(self):
        self.guard.register_verified_correction(Correction("c", "v1", ("e1",)))
        with self.assertRaises(ValueError):
            self.guard.register_verified_correction(Correction("c", "v2", ("e2",)))

    def test_identity_uses_independent_binding_not_self_label(self):
        host = Identity("agent-a", "provider-a", "model-a", "role-a")
        wrong = replace(host, provider_id="provider-b", model_id="model-b")
        self.assertEqual(self.guard.check_self_identity(wrong, actor_id="agent-a").status, "identity_unknown_no_host_binding")
        with self.assertRaises(ValueError):
            self.guard.mark_verified_identity_correction("agent-a")
        self.guard.register_host_identity(host)
        self.assertEqual(self.guard.check_self_identity(host, actor_id="agent-a").status, "identity_matches_host_binding")
        mismatch = self.guard.check_self_identity(wrong, actor_id="agent-a")
        self.assertEqual(mismatch.status, "identity_mismatch")
        self.assertTrue(mismatch.intervention)
        self.guard.mark_verified_identity_correction("agent-a")
        replay = self.guard.check_self_identity(wrong, actor_id="agent-a")
        self.assertEqual(replay.status, "identity_mismatch_after_verified_correction")
        self.assertFalse(replay.intervention)
        self.assertEqual(self.guard.check_self_identity(replace(host, role_id="role-b"), actor_id="agent-a").status,
                         "identity_mismatch_after_verified_correction")
        with self.assertRaises(ValueError):
            self.guard.register_host_identity(wrong)
        other = Identity("agent-b", "provider-b", "model-b", "role-b")
        self.guard.register_host_identity(other)
        self.assertEqual(self.guard.check_self_identity(other, actor_id="agent-a").status,
                         "identity_mismatch_after_verified_correction")
        self.assertEqual(self.guard.check_self_identity(other, actor_id="agent-b").status,
                         "identity_matches_host_binding")

    def test_attribution(self):
        self.assertEqual(self.guard.check_attribution("u1", "speaker-a").status, "attribution_unverified")
        kwargs = dict(asserted_quote_sha256="a" * 64, verified_quote_sha256="a" * 64)
        self.assertEqual(self.guard.check_attribution("u1", "speaker-a", verified_speaker_id="speaker-b",
                                                      **kwargs).status, "attribution_mismatch")
        self.assertEqual(self.guard.check_attribution("u1", "speaker-a", verified_speaker_id="speaker-a",
                                                      **kwargs).status, "attribution_confirmed")
        kwargs["asserted_quote_sha256"] = "b" * 64
        self.assertEqual(self.guard.check_attribution("u1", "speaker-a", verified_speaker_id="speaker-a",
                                                      **kwargs).status, "attribution_mismatch")
        for bad in (None, "unsupported-digest", 1, "A" * 64):
            for field in ("asserted_quote_sha256", "verified_quote_sha256"):
                malformed = dict(kwargs, **{field: bad})
                self.assertEqual(self.guard.check_attribution("u1", "speaker-a", verified_speaker_id="speaker-a",
                                                              **malformed).status, "attribution_unverified")

    def test_clarifying_non_advocacy_turns_not_counted(self):
        for index in range(3):
            result = self.guard.observe_turn(PersuasionTurn("d", "clarify-" + str(index), "c",
                                                            advocacy=False), actor_id="actor-a")
            self.assertEqual(result.status, "non_advocacy_not_counted")
            self.assertFalse(result.intervention)
        self.assertEqual(self.guard.observe_turn(PersuasionTurn("d", "first", "c"), actor_id="actor-a").status, "no_indicator")
        self.assertTrue(self.guard.observe_turn(PersuasionTurn("d", "second", "c"), actor_id="actor-a").intervention)

    def test_repeat_no_evidence_and_changed_criterion_are_only_indicators(self):
        first = PersuasionTurn("decision-1", "turn-1", "criterion-1", ("e1",))
        self.assertEqual(self.guard.observe_turn(first, actor_id="actor-a").status, "no_indicator")
        repeated = self.guard.observe_turn(replace(first, turn_id="turn-2"), actor_id="actor-a")
        self.assertTrue(repeated.intervention)
        self.assertIn("observed_no_new_evidence_ids", repeated.indicators)
        changed = self.guard.observe_turn(replace(first, turn_id="turn-3", criterion_id="criterion-2",
                                                  unanswered_objection_hypothesis=True), actor_id="actor-a")
        self.assertFalse(changed.intervention)
        self.assertIn("untrusted_unanswered_objection_hypothesis", changed.indicators)
        self.assertIn("observed_criterion_change_not_inherently_wrong", changed.indicators)

    def test_new_evidence_does_not_trigger_repeat_indicator(self):
        self.guard.observe_turn(PersuasionTurn("d", "t1", "c", ("e1",)), actor_id="actor-a")
        result = self.guard.observe_turn(PersuasionTurn("d", "t2", "c", ("e2",)), actor_id="actor-a")
        self.assertEqual(result.status, "no_indicator")

    def test_duplicate_delivery_not_persuasion_and_overwrite_rejected(self):
        turn = PersuasionTurn("d", "t", "c")
        self.guard.observe_turn(turn, actor_id="actor-a")
        self.assertEqual(self.guard.observe_turn(turn, actor_id="actor-a").status, "duplicate_delivery")
        with self.assertRaises(ValueError):
            self.guard.observe_turn(replace(turn, criterion_id="changed"), actor_id="actor-a")

    def test_budget_and_single_intervention_across_status_changes(self):
        guard = ConversationGuard("session-2", 1)
        self.assertTrue(guard.check_completion(self.action).intervention)
        self.assertFalse(guard.check_completion(self.action, Receipt(self.action, ReceiptState.PENDING)).intervention)
        result = guard.check_attribution("u", "speaker")
        self.assertFalse(result.intervention)
        self.assertEqual(result.next_step, "none")
        self.assertEqual(result.status, "attribution_unverified")

    def test_different_actor_first_disagreement_not_repeat(self):
        turn = PersuasionTurn("d", "t1", "c", ("e1",))
        self.guard.observe_turn(turn, actor_id="actor-a")
        result = self.guard.observe_turn(turn, actor_id="actor-b")
        self.assertEqual(result.status, "no_indicator")
        self.assertFalse(result.intervention)
        repeated = self.guard.observe_turn(replace(turn, turn_id="t2"), actor_id="actor-a")
        self.assertTrue(repeated.intervention)
        with self.assertRaises(TypeError):
            self.guard.observe_turn(turn)

    def test_criterion_change_with_new_evidence_is_advisory(self):
        guard = ConversationGuard("session", 1, pressure_budget=1)
        guard.observe_turn(PersuasionTurn("d", "t1", "c1", ("e1",)), actor_id="actor-a")
        changed = guard.observe_turn(PersuasionTurn("d", "t2", "c2", ("e2",)), actor_id="actor-a")
        self.assertEqual(changed.status, "changed_criterion_advisory")
        self.assertFalse(changed.intervention)
        flag = guard.observe_turn(PersuasionTurn("other", "t3", "c", unanswered_objection_hypothesis=True),
                                  actor_id="actor-a")
        self.assertFalse(flag.intervention)
        repeat = guard.observe_turn(PersuasionTurn("d", "t4", "c2", ("e2",)), actor_id="actor-a")
        self.assertTrue(repeat.intervention)
        self.assertTrue(guard.check_completion(self.action).intervention)

    def test_pressure_cannot_starve_reserved_security_budget(self):
        guard = ConversationGuard("session", 1, pressure_budget=1)
        for decision in ("d1", "d2", "d3"):
            guard.observe_turn(PersuasionTurn(decision, decision + "a", "c"), actor_id="actor-a")
            result = guard.observe_turn(PersuasionTurn(decision, decision + "b", "c"), actor_id="actor-a")
            self.assertEqual(result.intervention, decision == "d1")
        self.assertTrue(guard.check_completion(self.action).intervention)

    def test_unverified_evidence_id_only_new_once(self):
        self.guard.register_verified_correction(Correction("c", "v", ("verified",)))
        claim = Claim("c", "contradicted", ("unverified",))
        self.assertEqual(self.guard.check_claim(claim).status, "new_evidence_needs_review")
        repeated = self.guard.check_claim(claim)
        self.assertEqual(repeated.status, "conflicts_with_verified_correction")
        self.assertTrue(repeated.intervention)
        self.assertEqual(self.guard.check_claim(replace(claim, evidence_ids=("new-id",))).status,
                         "new_evidence_needs_review")

    def test_validation(self):
        for identifier in ("", "Not Canonical", " transcript ", None):
            with self.assertRaises(ValueError):
                ConversationGuard(identifier)
        for budget in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                ConversationGuard("session", budget)
        with self.assertRaises(ValueError):
            Correction("claim", "value", ())
        with self.assertRaises(ValueError):
            Receipt(self.action, "confirmed")
        with self.assertRaises(ValueError):
            Claim("claim", "value", ["mutable"])


class RepeatCounterTests(unittest.TestCase):
    def test_verified_correction_window_and_dedup(self):
        counter = RepeatCounter("session", "case", "wrong", "correction", corrected_at_ms=100, window_ms=50)
        self.assertEqual(counter.observe("pre", "wrong", observed_at_ms=99).count, 0)
        same = counter.observe("same-time", "wrong", observed_at_ms=100)
        self.assertEqual((same.status, same.count), ("at_correction_time_excluded", 0))
        first = counter.observe("e1", "wrong", observed_at_ms=110)
        self.assertEqual((first.count, first.elapsed_ms), (1, 10))
        self.assertEqual(counter.observe("e1", "wrong", observed_at_ms=110).count, 1)
        self.assertEqual(counter.observe("quote", "wrong", observed_at_ms=120, asserted=False).count, 1)
        self.assertEqual(counter.observe("different", "other", observed_at_ms=125).count, 1)
        late = counter.observe("late", "wrong", observed_at_ms=115)
        self.assertEqual((late.status, late.count), ("late_event_excluded", 1))
        boundary = counter.observe("boundary", "wrong", observed_at_ms=150)
        self.assertEqual((boundary.count, boundary.elapsed_ms), (2, 50))
        outside = counter.observe("outside", "wrong", observed_at_ms=151)
        self.assertEqual((outside.status, outside.count), ("outside_window", 2))
        with self.assertRaises(ValueError):
            counter.observe("e1", "wrong", observed_at_ms=111)

    def test_no_implicit_or_invalid_timestamps(self):
        for bad in (True, -1, 1.5, None):
            with self.assertRaises(ValueError):
                RepeatCounter("session", "case", "wrong", "correction", corrected_at_ms=bad, window_ms=50)
        counter = RepeatCounter("session", "case", "wrong", "correction", corrected_at_ms=0, window_ms=50)
        with self.assertRaises(ValueError):
            counter.observe("event", "wrong", observed_at_ms=True)
        with self.assertRaises(TypeError):
            counter.observe("event", "wrong")


class UntrustedObjectionTests(unittest.TestCase):
    def test_untrusted_objection_alone_does_not_spend_intervention(self):
        guard = ConversationGuard("session", intervention_budget=1)
        first = guard.observe_turn(PersuasionTurn("decision", "turn-one", "criterion", (), True), actor_id="actor-a")
        self.assertEqual(first.status, "unverified_hypothesis_only")
        self.assertFalse(first.intervention)
        second = guard.observe_turn(PersuasionTurn("decision", "turn-two", "criterion"), actor_id="actor-a")
        self.assertTrue(second.intervention)


if __name__ == "__main__":
    unittest.main()
