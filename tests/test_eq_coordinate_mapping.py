import unittest

from eqgps.coordinates import loc_to_map_point
from eqgps.heading import HeadingTracker
from eqgps.parser import Loc, parse_sense_heading_line


class EqCoordinateMappingTests(unittest.TestCase):
    def test_oasis_east_movement_from_loc_moves_map_x_positive(self):
        first = loc_to_map_point(Loc(-492.35, 310.84, 26.23))
        second = loc_to_map_point(Loc(-492.74, 305.47, 24.02))
        self.assertGreater(second.x, first.x)

    def test_oasis_east_movement_is_not_primarily_vertical(self):
        first = loc_to_map_point(Loc(-492.35, 310.84, 26.23))
        second = loc_to_map_point(Loc(-492.74, 305.47, 24.02))
        horizontal_delta = abs(second.x - first.x)
        vertical_delta = abs(second.y - first.y)
        self.assertGreater(horizontal_delta, vertical_delta)

    def test_heading_tracker_uses_mapped_coordinates_so_oasis_sample_points_east(self):
        tracker = HeadingTracker(min_distance=3.0)
        tracker.add_sample(Loc(-492.35, 310.84, 26.23))
        heading = tracker.add_sample(Loc(-492.74, 305.47, 24.02))
        self.assertIsNotNone(heading)
        self.assertTrue(heading < 10.0 or heading > 350.0)

    def test_parse_sense_heading_line(self):
        line = "[Thu Jun 04 22:41:01 2026] You think you are heading East."
        self.assertEqual(parse_sense_heading_line(line), "East")


if __name__ == "__main__":
    unittest.main()
