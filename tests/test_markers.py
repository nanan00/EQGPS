import time
import unittest

from eqgps.markers import (
    Marker,
    MarkerStore,
    clear_marker_timer,
    marker_timer_state,
    normalize_timer_minutes,
    reset_marker_timer,
    reset_marker_timer_paused,
    update_marker_details,
)


class MarkerTests(unittest.TestCase):
    def test_marker_store_round_trips_zone_markers_and_waypoint(self):
        store = MarkerStore()
        marker = Marker(zone_key="ecommons", x=100.0, y=-200.0, label="Orc Camp", category="Spawn")
        store.add(marker)
        store.set_waypoint(marker.id)

        data = store.to_dict()
        loaded = MarkerStore.from_dict(data)

        self.assertEqual(len(loaded.for_zone("ecommons")), 1)
        self.assertEqual(loaded.active_waypoint_id, marker.id)
        self.assertEqual(loaded.for_zone("ecommons")[0].label, "Orc Camp")

    def test_marker_timer_state_reports_ready_when_expired(self):
        marker = Marker(
            zone_key="ecommons",
            x=0.0,
            y=0.0,
            label="spawn",
            timer_minutes=6,
            timer_started_at=time.time() - 7 * 60,
        )

        state = marker_timer_state(marker, now=time.time())

        self.assertEqual(state, "READY")

    def test_marker_timer_state_reports_remaining_minutes(self):
        marker = Marker(
            zone_key="ecommons",
            x=0.0,
            y=0.0,
            label="spawn",
            timer_minutes=6,
            timer_started_at=100.0,
        )

        state = marker_timer_state(marker, now=100.0 + 2 * 60)

        self.assertEqual(state, "4:00")

    def test_search_filters_by_zone_label_category_and_notes(self):
        store = MarkerStore([
            Marker(zone_key="freportw", x=1, y=2, label="Bank", category="Vendor", notes="coins"),
            Marker(zone_key="freportw", x=3, y=4, label="Guard Spawn", category="Spawn", notes="six minute"),
            Marker(zone_key="ecommons", x=5, y=6, label="Orc Camp", category="Camp"),
        ])

        results = store.search(zone_key="freportw", query="spawn")

        self.assertEqual([marker.label for marker in results], ["Guard Spawn"])

    def test_categories_for_zone_are_sorted(self):
        store = MarkerStore([
            Marker(zone_key="freportw", x=1, y=2, label="Bank", category="Vendor"),
            Marker(zone_key="freportw", x=3, y=4, label="Guard", category="Spawn"),
            Marker(zone_key="ecommons", x=5, y=6, label="Orc", category="Camp"),
        ])

        self.assertEqual(store.categories_for_zone("freportw"), ["Spawn", "Vendor"])

    def test_merge_import_replaces_duplicate_ids_and_keeps_existing(self):
        existing = Marker(zone_key="freportw", x=1, y=2, label="Old", id="same")
        incoming = Marker(zone_key="freportw", x=9, y=8, label="New", id="same")
        other = Marker(zone_key="freportw", x=3, y=4, label="Other", id="other")
        store = MarkerStore([existing, other])

        store.merge_import(MarkerStore([incoming]))

        self.assertEqual([marker.label for marker in store.markers], ["Other", "New"])
    def test_normalize_timer_minutes_supports_one_minute_steps_in_eq_spawn_range(self):
        self.assertEqual(normalize_timer_minutes("14"), 14)
        self.assertEqual(normalize_timer_minutes("28"), 28)
        self.assertEqual(normalize_timer_minutes("19.8"), 20)

    def test_normalize_timer_minutes_defaults_to_common_eq_spawn_timer(self):
        self.assertEqual(normalize_timer_minutes(""), 18)
        self.assertEqual(normalize_timer_minutes("not a number"), 18)
        self.assertEqual(normalize_timer_minutes("0"), 1)

    def test_reset_marker_timer_restarts_existing_timer_and_can_update_minutes(self):
        marker = Marker(zone_key="ecommons", x=0, y=0, label="spawn", timer_minutes=18, timer_started_at=100.0)

        reset_marker_timer(marker, minutes=22, now=500.0)

        self.assertEqual(marker.timer_minutes, 22)
        self.assertEqual(marker.timer_started_at, 500.0)
        self.assertEqual(marker_timer_state(marker, now=500.0), "22:00")

    def test_reset_marker_timer_paused_keeps_duration_but_stops_countdown_until_started(self):
        marker = Marker(zone_key="ecommons", x=0, y=0, label="spawn", timer_minutes=18, timer_started_at=100.0)

        reset_marker_timer_paused(marker, minutes=22)

        self.assertEqual(marker.timer_minutes, 22)
        self.assertIsNone(marker.timer_started_at)
        self.assertIsNone(marker_timer_state(marker, now=500.0))

        reset_marker_timer(marker, minutes=marker.timer_minutes, now=500.0)

        self.assertEqual(marker_timer_state(marker, now=500.0), "22:00")

    def test_clear_marker_timer_removes_existing_timer(self):
        marker = Marker(zone_key="ecommons", x=0, y=0, label="spawn", timer_minutes=18, timer_started_at=100.0)

        clear_marker_timer(marker)

        self.assertIsNone(marker.timer_minutes)
        self.assertIsNone(marker.timer_started_at)
        self.assertIsNone(marker_timer_state(marker, now=500.0))
    def test_update_marker_details_edits_existing_marker_without_losing_timer(self):
        marker = Marker(
            zone_key="ecommons",
            x=1,
            y=2,
            label="Old",
            category="Spawn",
            notes="old notes",
            timer_minutes=18,
            timer_started_at=100.0,
        )

        update_marker_details(marker, label="Named PH", category="Camp", notes="respawns 14-28")

        self.assertEqual(marker.label, "Named PH")
        self.assertEqual(marker.category, "Camp")
        self.assertEqual(marker.notes, "respawns 14-28")
        self.assertEqual(marker.timer_minutes, 18)
        self.assertEqual(marker.timer_started_at, 100.0)

    def test_corrupt_imported_marker_records_are_skipped_without_losing_valid_markers(self):
        loaded = MarkerStore.from_dict(
            {
                "active_waypoint_id": "bad-marker",
                "markers": [
                    {"id": "bad-marker", "zone_key": "ecommons", "x": "oops", "y": 2, "label": "Broken"},
                    {"id": "good-marker", "zone_key": "ecommons", "x": 10, "y": 20, "label": "Valid"},
                ],
            }
        )

        self.assertEqual([marker.label for marker in loaded.markers], ["Valid"])
        self.assertIsNone(loaded.active_waypoint_id)


if __name__ == "__main__":
    unittest.main()
