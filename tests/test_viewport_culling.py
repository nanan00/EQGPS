import unittest

from eqgps.viewport import point_on_screen, segment_on_screen


class SegmentCullingTests(unittest.TestCase):
    def test_segment_fully_inside_is_visible(self):
        self.assertTrue(segment_on_screen(10, 10, 100, 100, 800, 600))

    def test_segment_crossing_edge_is_visible(self):
        # One endpoint off the left edge, the other on-screen.
        self.assertTrue(segment_on_screen(-200, 300, 50, 300, 800, 600))

    def test_segment_far_left_is_culled(self):
        self.assertFalse(segment_on_screen(-500, 300, -400, 300, 800, 600))

    def test_segment_far_right_is_culled(self):
        self.assertFalse(segment_on_screen(900, 300, 1000, 300, 800, 600))

    def test_segment_far_above_is_culled(self):
        self.assertFalse(segment_on_screen(100, -500, 200, -400, 800, 600))

    def test_segment_far_below_is_culled(self):
        self.assertFalse(segment_on_screen(100, 900, 200, 1000, 800, 600))

    def test_segment_just_off_edge_within_margin_is_visible(self):
        # Within the default 32px margin, so line caps near the edge still draw.
        self.assertTrue(segment_on_screen(-10, 300, -5, 300, 800, 600))


class PointCullingTests(unittest.TestCase):
    def test_point_inside_is_visible(self):
        self.assertTrue(point_on_screen(400, 300, 800, 600))

    def test_point_far_off_is_culled(self):
        self.assertFalse(point_on_screen(-500, 300, 800, 600))
        self.assertFalse(point_on_screen(400, 5000, 800, 600))

    def test_point_within_margin_is_visible(self):
        # Labels can extend past their anchor, so a generous margin keeps
        # near-edge labels drawn.
        self.assertTrue(point_on_screen(-40, 300, 800, 600))


if __name__ == "__main__":
    unittest.main()
