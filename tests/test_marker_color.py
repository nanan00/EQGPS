import unittest

from eqgps.markers import Marker, normalize_marker_color, update_marker_details


class MarkerColorTests(unittest.TestCase):
    def test_valid_six_digit_hex_is_kept(self):
        self.assertEqual(normalize_marker_color("#1a2b3c"), "#1a2b3c")

    def test_valid_three_digit_hex_is_kept(self):
        self.assertEqual(normalize_marker_color("#abc"), "#abc")

    def test_invalid_color_falls_back_to_default(self):
        self.assertEqual(normalize_marker_color("not-a-color"), "#ffcc00")
        self.assertEqual(normalize_marker_color("123456"), "#ffcc00")
        self.assertEqual(normalize_marker_color("#12g456"), "#ffcc00")
        self.assertEqual(normalize_marker_color(None), "#ffcc00")

    def test_custom_default_is_respected(self):
        self.assertEqual(normalize_marker_color("bad", default="#00ff00"), "#00ff00")

    def test_from_dict_sanitizes_bad_color(self):
        marker = Marker.from_dict({"zone_key": "z", "x": 1.0, "y": 2.0, "label": "m", "color": "bogus"})
        self.assertEqual(marker.color, "#ffcc00")

    def test_update_marker_details_applies_valid_color(self):
        marker = Marker(zone_key="z", x=0.0, y=0.0, label="m")
        update_marker_details(marker, label="m", category="Spawn", notes="", color="#ff0000")
        self.assertEqual(marker.color, "#ff0000")

    def test_update_marker_details_ignores_bad_color_keeps_existing(self):
        marker = Marker(zone_key="z", x=0.0, y=0.0, label="m", color="#123123")
        update_marker_details(marker, label="m", category="Spawn", notes="", color="nope")
        self.assertEqual(marker.color, "#123123")

    def test_update_marker_details_without_color_leaves_color_untouched(self):
        marker = Marker(zone_key="z", x=0.0, y=0.0, label="m", color="#abcabc")
        update_marker_details(marker, label="new", category="Spawn", notes="")
        self.assertEqual(marker.color, "#abcabc")


if __name__ == "__main__":
    unittest.main()
