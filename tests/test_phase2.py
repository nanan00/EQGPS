import math
import unittest

from eqgps.heading import HeadingTracker
from eqgps.viewport import ViewportTransform, clamp_pan_units, fit_viewport_to_bounds
from eqgps.parser import Loc


class Phase2Tests(unittest.TestCase):
    def test_viewport_world_screen_round_trip(self):
        viewport = ViewportTransform(bounds=(-100.0, -50.0, 300.0, 150.0), scale=2.0, offset_x=10.0, offset_y=20.0)
        sx, sy = viewport.world_to_screen(25.0, 75.0)
        wx, wy = viewport.screen_to_world(sx, sy)
        self.assertAlmostEqual(wx, 25.0)
        self.assertAlmostEqual(wy, 75.0)

    def test_distance_between_world_points(self):
        viewport = ViewportTransform(bounds=(0.0, 0.0, 100.0, 100.0), scale=1.0, offset_x=0.0, offset_y=0.0)
        self.assertEqual(viewport.distance((0.0, 0.0), (3.0, 4.0)), 5.0)

    def test_pan_is_clamped_to_10000_world_units(self):
        x, y = clamp_pan_units(20000.0, -25000.0, scale=2.0, max_units=10000.0)
        self.assertEqual(x, 20000.0)
        self.assertEqual(y, -20000.0)

    def test_fit_viewport_ignores_unrealized_tiny_canvas_size(self):
        self.assertIsNone(fit_viewport_to_bounds((0.0, 0.0, 1000.0, 500.0), canvas_width=1, canvas_height=1))

    def test_fit_viewport_computes_scale_and_offsets_for_real_canvas(self):
        fit = fit_viewport_to_bounds((0.0, 0.0, 1000.0, 500.0), canvas_width=1100, canvas_height=700)
        self.assertIsNotNone(fit)
        scale, offset_x, offset_y = fit
        self.assertAlmostEqual(scale, 1.04)
        self.assertGreaterEqual(offset_x, 30.0)
        self.assertGreaterEqual(offset_y, 30.0)

    def test_heading_updates_when_movement_exceeds_threshold(self):
        tracker = HeadingTracker(min_distance=3.0)
        self.assertIsNone(tracker.add_sample(Loc(0.0, 0.0, 0.0)))
        heading = tracker.add_sample(Loc(0.0, -10.0, 0.0))
        self.assertAlmostEqual(heading, 0.0)

    def test_heading_keeps_previous_when_movement_too_small(self):
        tracker = HeadingTracker(min_distance=3.0)
        tracker.add_sample(Loc(0.0, 0.0, 0.0))
        tracker.add_sample(Loc(0.0, -10.0, 0.0))
        heading = tracker.add_sample(Loc(0.1, -10.5, 0.0))
        self.assertAlmostEqual(heading, 0.0)


if __name__ == "__main__":
    unittest.main()
