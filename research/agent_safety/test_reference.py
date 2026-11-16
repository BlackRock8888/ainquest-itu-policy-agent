"""Synthetic unit cases; not provider comparisons, held-out eval or security proof."""
import unittest
from dataclasses import replace
from reference import (Evidence, EvidenceLedger, BoundedCheck, ActionRequest,
                       Approval, OwnerGate, Layer, Review, candidate_digest, admit_layers)


class EvidenceTests(unittest.TestCase):
    def test_duplicates_do_not_corroborate(self):
        ledger = EvidenceLedger()
        for i in range(10):
            ledger.ingest(Evidence(str(i), "same-origin", 1, 1))
        self.assertEqual(ledger.snapshot()["corroborators"], 1)
        checker = BoundedCheck()
        self.assertEqual(checker.step(ledger)[0], "check_more")
        self.assertEqual(checker.step(ledger)[0], "stop_unknown")

    def test_metadata_and_weaker_mirrors_do_not_extend_checks(self):
        for update in (Evidence("a", "one", 2, 1.0),
                       Evidence("mirror", "one", 1, 1),
                       Evidence("weak-mirror", "one", 1, .1),
                       Evidence("zero", "empty", 1, 0)):
            with self.subTest(update=update):
                ledger, checker = EvidenceLedger(), BoundedCheck(10)
                ledger.ingest(Evidence("a", "one", 1, 1))
                decision, before = checker.step(ledger)
                self.assertEqual(decision, "check_more")
                ledger.ingest(update)
                decision, after = checker.step(ledger)
                self.assertNotEqual(before["raw_digest"], after["raw_digest"])
                self.assertEqual(before["effective_digest"], after["effective_digest"])
                self.assertEqual(decision, "stop_unknown")

    def test_independent_evidence_then_withdrawal(self):
        ledger = EvidenceLedger()
        ledger.ingest(Evidence("a", "one", 1, 1))
        ledger.ingest(Evidence("b", "two", 1, 1))
        self.assertEqual(BoundedCheck().step(ledger)[0], "accept_provisionally")
        ledger.ingest(Evidence("b", "two", 2, 1, active=False))
        self.assertEqual(BoundedCheck(max_rounds=1).step(ledger)[0], "stop_unknown")

    def test_strong_counterevidence_vetoes(self):
        ledger = EvidenceLedger()
        for i in range(20):
            ledger.ingest(Evidence(str(i), str(i), 1, 1))
        ledger.ingest(Evidence("opponent", "independent", 1, 0, .9))
        self.assertEqual(BoundedCheck().step(ledger)[0], "escalate_conflict")

    def test_origin_withdrawal_invalidates_mirrors(self):
        ledger = EvidenceLedger()
        for source, group in (("a", "one"), ("mirror-a", "one"), ("b", "two")):
            ledger.ingest(Evidence(source, group, 1, 1))
        self.assertTrue(ledger.snapshot()["qualified"])
        ledger.withdraw_origin("one")
        self.assertFalse(ledger.snapshot()["qualified"])
        ledger.ingest(Evidence("late-mirror", "one", 1, 1))
        self.assertFalse(ledger.snapshot()["qualified"])

    def test_withdrawn_source_cannot_reappear_under_new_origin(self):
        ledger = EvidenceLedger()
        ledger.ingest(Evidence("a", "one", 1, 1))
        ledger.ingest(Evidence("b", "two", 1, 1))
        ledger.withdraw_origin("one")
        for group in ("two", "invented-independent-origin"):
            with self.assertRaisesRegex(ValueError, "provenance is sticky"):
                ledger.ingest(Evidence("a", group, 2, 1))
        # A valid newer revision still belongs to the withdrawn group.
        ledger.ingest(Evidence("a", "one", 2, 1))
        self.assertFalse(ledger.snapshot()["qualified"])
        self.assertEqual(ledger.snapshot()["corroborators"], 1)

    def test_doubt_threshold_and_weak_opposition(self):
        ledger = EvidenceLedger()
        for source in ("a", "b"):
            ledger.ingest(Evidence(source, source, 1, .75))
        at_boundary = ledger.snapshot()
        self.assertEqual(at_boundary["doubt_index"], .25)
        self.assertTrue(at_boundary["qualified"])
        for i in range(4):
            ledger.ingest(Evidence(str(i), str(i), 1, 0, .5))
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot["support_strength"], 1.5)
        self.assertEqual(snapshot["opposition_strength"], 2)
        self.assertEqual(snapshot["doubt_index"], 1)
        self.assertFalse(snapshot["conflict"])
        self.assertFalse(snapshot["qualified"])
        self.assertEqual(BoundedCheck(1).step(ledger)[0], "stop_unknown")

    def test_numeric_evidence_types(self):
        for revision in (True, 1.0, "1", None):
            with self.assertRaises(ValueError):
                Evidence("a", "one", revision, 1)
        for field in ("support", "oppose"):
            for strength in (True, False, "0.5", None):
                with self.assertRaises(ValueError):
                    replace(Evidence("a", "one", 1, .5), **{field: strength})

    def test_round_budget_and_terminal(self):
        ledger, checker = EvidenceLedger(), BoundedCheck(2)
        self.assertEqual(checker.step(ledger)[0], "check_more")
        ledger.ingest(Evidence("a", "one", 1, .2))
        self.assertEqual(checker.step(ledger)[0], "stop_unknown")
        with self.assertRaises(ValueError):
            checker.step(ledger)

    def test_invalid_evidence_and_stale_updates(self):
        for strength in (float("nan"), float("inf"), -1, 2):
            with self.assertRaises(ValueError):
                Evidence("a", "one", 1, strength)
        ledger = EvidenceLedger()
        ledger.ingest(Evidence("a", "one", 2, .9))
        with self.assertRaises(ValueError):
            ledger.ingest(Evidence("a", "one", 1, 1))


class GateTests(unittest.TestCase):
    def setUp(self):
        self.req = ActionRequest("id-1", "send", "recipient-A", "a" * 64)
        self.approval = Approval(self.req, 100)
        self.gate = OwnerGate({"send"})

    def evaluate(self, request=None, approval=None, origin="authenticated_owner_ui", now=1):
        return self.gate.evaluate(request or self.req, approval or self.approval,
                                  trusted_origin=origin, now=now)

    def test_model_cannot_approve(self):
        self.assertEqual(self.evaluate(origin="model"), "deny_untrusted_approval")

    def test_scope_and_expiry(self):
        for req in (replace(self.req, request_id="id-2"), replace(self.req, recipient="B"),
                    replace(self.req, payload_sha256="b" * 64)):
            self.assertEqual(self.evaluate(req), "deny_scope_or_expiry")
        self.assertEqual(self.evaluate(now=100), "deny_scope_or_expiry")

    def test_policy_cannot_be_expanded_by_approval(self):
        req = replace(self.req, action="delete")
        self.assertEqual(self.evaluate(req, Approval(req, 100)), "deny_policy")

    def test_once_not_execution(self):
        self.assertEqual(self.evaluate(), "permitted_once")
        self.assertEqual(self.evaluate(), "deny_replay")

    def test_malformed_digest_denied(self):
        req = replace(self.req, payload_sha256="not-a-digest")
        self.assertEqual(self.evaluate(req, Approval(req, 100)), "deny_payload_digest")

    def test_nonstring_payload_digest_denied(self):
        for digest in (None, 1, True, b"a" * 64, ["a"] * 64):
            req = replace(self.req, payload_sha256=digest)
            self.assertEqual(self.evaluate(req, Approval(req, 100)), "deny_payload_digest")

    def test_bare_string_allowlist_rejected(self):
        for actions in ("send", b"send"):
            with self.assertRaises(ValueError):
                OwnerGate(actions)

    def test_invalid_clock_denied(self):
        self.assertEqual(self.evaluate(now=float("nan")), "deny_clock")
        self.assertEqual(self.evaluate(approval=Approval(self.req, float("nan"))),
                         "deny_scope_or_expiry")


class LayerTests(unittest.TestCase):
    def reviews(self, layers):
        digest = candidate_digest(layers)
        return [Review(a.participant, b.participant, digest, "critique", "proposal",
                       "proposed correction", "synthetic acceptance check", True)
                for a, b in ([(a, a) for a in layers] +
                             [(a, b) for a in layers for b in layers if a != b])]

    def admit(self, old, new, reviews=None, approval=None):
        return admit_layers(old, new, self.reviews(new) if reviews is None else reviews,
                            owner_approved_digest=candidate_digest(new) if approval is None else approval)

    def test_canonical_participant_ids(self):
        for participant in ("", "  ", " a", "a ", "A", None):
            with self.assertRaises(ValueError):
                self.admit((), (Layer(participant, 1, ("r",)),))

    def test_incremental_reciprocal_layers(self):
        old = ()
        for name in ("participant-a", "participant-b", "participant-c", "participant-d"):
            new = old + (Layer(name, 1, ("self-protection proposal",)),)
            self.assertEqual(self.admit(old, new), new)
            old = new

    def test_self_review_phase_must_finish_before_peer_phase(self):
        layers = (Layer("a", 1, ("r",)), Layer("b", 1, ("s",)))
        reviews = self.reviews(layers)
        reviews[1], reviews[2] = reviews[2], reviews[1]
        with self.assertRaisesRegex(ValueError, "self-reviews must precede"):
            self.admit((), layers, reviews)

    def test_acceptance_test_and_correction_required_separately(self):
        layers = (Layer("a", 1, ("r",)),)
        for field in ("acceptance_test", "correction"):
            for missing in ("", "   ", None):
                with self.subTest(field=field, missing=missing):
                    review = replace(self.reviews(layers)[0], **{field: missing})
                    with self.assertRaises(ValueError):
                        self.admit((), layers, [review])

    def test_missing_self_or_peer_review(self):
        layers = (Layer("a", 1, ("r",)), Layer("b", 1, ("s",)))
        for drop in range(4):
            reviews = self.reviews(layers)
            del reviews[drop]
            with self.assertRaises(ValueError):
                self.admit((), layers, reviews)

    def test_no_unreviewed_or_unapproved_candidate(self):
        layers = (Layer("a", 1, ("r",)),)
        for reviews in ([replace(self.reviews(layers)[0], passed=False)],
                        [replace(self.reviews(layers)[0], candidate_digest="stale")],
                        self.reviews(layers) * 2):
            with self.assertRaises(ValueError):
                self.admit((), layers, reviews)
        with self.assertRaises(ValueError):
            self.admit((), layers, approval="model-generated")

    def test_no_deletion_or_reorder_or_silent_version_edit(self):
        old = (Layer("a", 1, ("r",)), Layer("b", 1, ("s",)))
        for new in (old[:1], old[::-1], (Layer("a", 1, ("r", "new")), old[1]),
                    (Layer("a", 2, ("replacement",)), old[1])):
            with self.assertRaises(ValueError):
                self.admit(old, new)
        self.assertEqual(self.admit(old, (Layer("a", 2, ("r", "new")), old[1]))[0].version, 2)


if __name__ == "__main__":
    unittest.main()
