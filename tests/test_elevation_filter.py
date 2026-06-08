import unittest

from eqgps.elevation import ElevationFilter, line_visible_at_player_z, label_visible_at_player_z
from eqgps.map_loader import MapLabel, MapLine


class ElevationFilterTests(unittest.TestCase):
    def test_disabled_filter_keeps_all_lines_visible(self):
        line = MapLine(0, 0, 500, 1, 1, 600, (255, 255, 255))
        elevation = ElevationFilter(enabled=False, above=10, below=10)

        self.assertTrue(line_visible_at_player_z(line, player_z=0, elevation=elevation))

    def test_line_visible_when_either_endpoint_is_inside_player_z_window(self):
        line = MapLine(0, 0, 120, 1, 1, 160, (255, 255, 255))
        elevation = ElevationFilter(enabled=True, above=25, below=15)

        self.assertTrue(line_visible_at_player_z(line, player_z=100, elevation=elevation))

    def test_line_hidden_when_both_endpoints_are_outside_player_z_window(self):
        line = MapLine(0, 0, 130, 1, 1, 160, (255, 255, 255))
        elevation = ElevationFilter(enabled=True, above=25, below=15)

        self.assertFalse(line_visible_at_player_z(line, player_z=100, elevation=elevation))

    def test_label_visible_only_inside_player_z_window(self):
        elevation = ElevationFilter(enabled=True, above=20, below=10)
        visible = MapLabel(0, 0, 90, (255, 255, 255), "visible")
        hidden = MapLabel(0, 0, 75, (255, 255, 255), "hidden")

        self.assertTrue(label_visible_at_player_z(visible, player_z=100, elevation=elevation))
        self.assertFalse(label_visible_at_player_z(hidden, player_z=100, elevation=elevation))

    def test_corrupt_saved_elevation_distances_fall_back_to_defaults(self):
        elevation = ElevationFilter.from_dict({"enabled": True, "above": "bad", "below": None})

        self.assertTrue(elevation.enabled)
        self.assertEqual(elevation.above, 50.0)
        self.assertEqual(elevation.below, 50.0)


if __name__ == "__main__":
    unittest.main()
