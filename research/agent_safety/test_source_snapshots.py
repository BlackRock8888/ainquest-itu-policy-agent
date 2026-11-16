"""Synthetic menu observations only; no real provider or source claims."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import unittest
from source_snapshots import Caption, Observation, SnapshotMemory


T0 = datetime(2026, 11, 16, 10, tzinfo=timezone.utc)


def menu(read_id="read-1", at=T0, price="12.00", date="2026-11-16"):
    return Observation(read_id, "https://example.invalid/menu", at, (
        Caption("Displayed menu date", "#menu-date", ("date",), date),
        Caption("Displayed soup price", "#soup-price", ("price", "trigger"), price, "AED")),
        source_created_raw="2023-04-01", source_published_raw="16 Nov 2026",
        external_revision="v1")


class SnapshotTests(unittest.TestCase):
    def test_menu_changes_preserve_old_date_price_and_order(self):
        memory = SnapshotMemory()
        first = memory.record(menu())
        later = memory.record(replace(menu("read-2", T0 + timedelta(days=1), "15.50", "2026-11-17"),
                                      source_published_raw="17 Nov 2026", external_revision="v2"))
        self.assertEqual(memory.get("read-1").captions[1].exact_value, "12.00")
        self.assertEqual(first.captions[0].exact_value, "2026-11-16")
        self.assertEqual(later.captions[1].exact_value, "15.50")
        self.assertNotEqual(first.brief_digest, later.brief_digest)
        self.assertEqual(later.captions[1].tags, ("price", "trigger"))
        self.assertEqual(later.captions[1].locator, "#soup-price")
        self.assertEqual(later.captions[1].unit, "AED")

    def test_creation_publication_unknown_are_not_access_time(self):
        memory = SnapshotMemory()
        first = memory.record(replace(menu(), source_created_raw=None, source_published_raw=None))
        later = memory.record(replace(menu("read-2", T0 + timedelta(days=1)),
                                      source_created_raw="2019 (as displayed)"))
        self.assertIsNone(first.source_created_raw)
        self.assertIsNone(first.source_published_raw)
        self.assertEqual(later.source_created_raw, "2019 (as displayed)")
        self.assertEqual(memory.access_bounds(first.source_id), (T0, T0 + timedelta(days=1)))

    def test_distinct_reads_out_of_order_and_duplicate_delivery(self):
        memory = SnapshotMemory()
        later = menu("read-2", T0 + timedelta(hours=1))
        memory.record(later)
        memory.record(menu())
        memory.record(later)
        self.assertEqual(len(memory.source_history(later.source_id)), 2)
        self.assertEqual(memory.access_bounds(later.source_id), (T0, later.observed_at))
        with self.assertRaises(ValueError):
            memory.access_bounds("unknown")

    def test_immutable_no_silent_overwrite(self):
        memory = SnapshotMemory()
        first = memory.record(menu())
        with self.assertRaises(FrozenInstanceError):
            first.source_created_raw = "changed"
        with self.assertRaises(FrozenInstanceError):
            first.captions[0].fact = "changed"
        with self.assertRaises(ValueError):
            memory.record(replace(first, source_created_raw="changed"))
        with self.assertRaises(ValueError):
            replace(first, captions=list(first.captions))
        with self.assertRaises(ValueError):
            Caption("fact", "#where", tags=["mutable"])

    def test_stable_brief_fingerprint_ignores_read_metadata(self):
        first = menu()
        later = replace(menu("read-2", T0 + timedelta(days=1)), external_revision="v999")
        self.assertEqual(first.brief_digest, later.brief_digest)
        self.assertEqual(first.brief_digest, menu().brief_digest)
        self.assertNotEqual(first.brief_digest, menu(price="12.0").brief_digest)
        self.assertNotEqual(first.brief_digest, replace(first, captions=first.captions[::-1]).brief_digest)

    def test_time_must_be_aware_and_normalized(self):
        with self.assertRaises(ValueError):
            menu(at=T0.replace(tzinfo=None))
        local = T0.astimezone(timezone(timedelta(hours=4)))
        self.assertEqual(menu(at=local).observed_at, T0)
        self.assertIs(menu(at=local).observed_at.tzinfo, timezone.utc)

    def test_exact_value_and_unit_validation(self):
        for value in (12.0, True, " "):
            with self.assertRaises(ValueError):
                Caption("price", "#price", exact_value=value)
        with self.assertRaises(ValueError):
            Caption("price", "#price", unit="AED")


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.memory = SnapshotMemory()
        self.memory.record(menu())
        self.initial = self.memory.revise("d1", "Soup displayed at 12 AED", "Initial observation", ("read-1",), claim_id="menu-price")

    def test_same_claim_cannot_create_second_root(self):
        with self.assertRaises(ValueError):
            self.memory.revise("d2", "Different conclusion", "No new evidence", ("read-1",),
                               claim_id="menu-price")
        for claim in ("", "  ", " menu-price", None):
            with self.assertRaises(ValueError):
                self.memory.revise("d2", "Statement", "Reason", ("read-1",), claim_id=claim)

    def test_independent_claim_roots_cross_claim_and_stale_parents(self):
        other = self.memory.revise("other-root", "Menu date", "Independent claim", ("read-1",),
                                   claim_id="menu-date")
        self.assertEqual(other.claim_id, "menu-date")
        self.memory.record(menu("read-2", T0 + timedelta(days=1), "15.50"))
        for claim, parent in (("menu-price", "other-root"), ("new-claim", "d1")):
            with self.assertRaises(ValueError):
                self.memory.revise("bad", "Statement", "Reason", ("read-2",),
                                   claim_id=claim, parent_id=parent)
        self.memory.revise("d2", "New price", "Price changed", ("read-2",),
                           claim_id="menu-price", parent_id="d1")
        self.memory.record(menu("read-3", T0 + timedelta(days=2), "20"))
        with self.assertRaises(ValueError):
            self.memory.revise("d3", "Newer price", "Price changed again", ("read-3",),
                               claim_id="menu-price", parent_id="d1")
        self.assertEqual(self.memory.decision("d1"), self.initial)

    def test_later_changed_content_revision_keeps_parent_and_reason(self):
        self.memory.record(menu("read-2", T0 + timedelta(days=1), "15.50"))
        revised = self.memory.revise("d2", "Soup now displayed at 15.50 AED", "Observed price changed",
                                     ("read-2",), claim_id="menu-price", parent_id="d1")
        self.assertEqual(revised.parent_id, "d1")
        self.assertEqual(revised.change_reason, "Observed price changed")
        self.assertEqual(self.memory.decision("d1"), self.initial)
        with self.assertRaises(FrozenInstanceError):
            revised.statement = "overwrite"

    def test_unchanged_repeat_or_revision_label_not_new_evidence(self):
        self.memory.record(replace(menu("read-2", T0 + timedelta(days=1)), external_revision="v2"))
        for references in (("read-1",), ("read-2",)):
            with self.assertRaises(ValueError):
                self.memory.revise("d2", "Different opinion", "No new facts", references, claim_id="menu-price", parent_id="d1")

    def test_presentation_and_metadata_changes_are_not_new_facts(self):
        first = menu()
        changed_caption = replace(first.captions[0], tags=("retagged",), locator="#new-location")
        alternatives = (
            replace(first, captions=(changed_caption, first.captions[1])),
            replace(first, captions=first.captions[::-1]),
            replace(first, captions=first.captions + (first.captions[0],)),
            replace(first, source_created_raw="relabeled", source_published_raw="relabeled"))
        for index, altered in enumerate(alternatives):
            read_id = "presentation-" + str(index)
            altered = replace(altered, read_id=read_id, observed_at=T0 + timedelta(days=1))
            self.memory.record(altered)
            self.assertNotEqual(first.brief_digest, altered.brief_digest)
            self.assertEqual(first.fact_digest, altered.fact_digest)
            with self.assertRaises(ValueError):
                self.memory.revise("d2", "No new fact", "Presentation only", (read_id,), claim_id="menu-price", parent_id="d1")

    def test_material_effective_date_change_permits_revision(self):
        first = menu()
        changed = replace(first.captions[1], effective_or_event_date_raw="2026-11-17")
        later = replace(first, read_id="dated", observed_at=T0 + timedelta(days=1),
                        captions=(first.captions[0], changed))
        self.memory.record(later)
        self.assertNotEqual(first.fact_digest, later.fact_digest)
        revision = self.memory.revise("d2", "Price applies on stated date", "New effective date observed",
                                      ("dated",), claim_id="menu-price", parent_id="d1")
        self.assertEqual(revision.parent_id, "d1")

    def test_new_source_reference_later_is_permitted_not_verified(self):
        self.memory.record(replace(menu("independent", T0 + timedelta(days=1)), source_id="source-B"))
        revision = self.memory.revise("d2", "Another source reports same price", "New source observed",
                                      ("independent",), claim_id="menu-price", parent_id="d1")
        self.assertEqual(revision.evidence_reads, ("independent",))

    def test_old_observation_cannot_be_used_as_later_fact(self):
        self.memory.record(menu("old", T0 - timedelta(days=1), "10"))
        with self.assertRaises(ValueError):
            self.memory.revise("d2", "Earlier menu", "Old evidence", ("old",), claim_id="menu-price", parent_id="d1")

    def test_later_observed_price_return_is_a_real_change(self):
        self.memory.record(menu("read-2", T0 + timedelta(days=1), "15.50"))
        self.memory.revise("d2", "New price", "New selected content", ("read-2",), claim_id="menu-price", parent_id="d1")
        self.memory.record(menu("read-3", T0 + timedelta(days=2)))
        revised = self.memory.revise("d3", "Price returned to 12 AED", "Observed price changed back",
                                     ("read-3",), claim_id="menu-price", parent_id="d2")
        self.assertEqual(revised.parent_id, "d2")

    def test_reject_missing_reason_evidence_parent_or_overwrite(self):
        for revision, reason, references, parent in (
                ("d2", "", ("read-1",), "d1"), ("d2", "reason", (), "d1"),
                ("d2", "reason", ("absent",), "d1"), ("d2", "reason", ("read-1",), "absent"),
                ("d1", "reason", ("read-1",), None)):
            with self.assertRaises(ValueError):
                self.memory.revise(revision, "Statement", reason, references, claim_id="menu-price", parent_id=parent)


if __name__ == "__main__":
    unittest.main()
