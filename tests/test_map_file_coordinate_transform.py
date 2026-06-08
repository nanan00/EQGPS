import tempfile
import textwrap
import unittest
from pathlib import Path

from eqgps.coordinates import loc_to_map_point, raw_map_file_xy_to_map_point
from eqgps.map_loader import parse_map_file
from eqgps.parser import Loc


class MapFileCoordinateTransformTests(unittest.TestCase):
    def test_player_loc_transform_keeps_east_as_positive_map_x(self):
        # Oasis evidence: moving east makes the second /loc number decrease, so
        # the player tracker must continue to use x=-loc_y and y=loc_x.
        start = loc_to_map_point(Loc(-492.35, 310.84, 26.23))
        end = loc_to_map_point(Loc(-493.93, 289.30, 17.86))

        self.assertGreater(end.x, start.x)

    def test_raw_map_file_points_are_flipped_top_to_bottom_only(self):
        # East Commonlands evidence: raw map geometry orientation was back to
        # being vertically flipped. Keep raw X but invert raw Y for map drawing.
        point = raw_map_file_xy_to_map_point(-3740.8036, -984.9999)

        self.assertAlmostEqual(point.x, -3740.8036)
        self.assertAlmostEqual(point.y, 984.9999)

    def test_parse_map_file_keeps_x_and_inverts_y_for_lines_and_labels(self):
        with tempfile.TemporaryDirectory() as td:
            map_file = Path(td) / "zone.txt"
            map_file.write_text(
                textwrap.dedent(
                    """
                    L -1, -2, 0, 3, 4, 0, 100, 100, 100
                    P 10, 20, 0, 255, 255, 255, Label Here
                    """
                ).strip(),
                encoding="utf-8",
            )

            parsed = parse_map_file(map_file)

            self.assertAlmostEqual(parsed.lines[0].x1, -1.0)
            self.assertAlmostEqual(parsed.lines[0].y1, 2.0)
            self.assertAlmostEqual(parsed.lines[0].x2, 3.0)
            self.assertAlmostEqual(parsed.lines[0].y2, -4.0)
            self.assertAlmostEqual(parsed.labels[0].x, 10.0)
            self.assertAlmostEqual(parsed.labels[0].y, -20.0)


if __name__ == "__main__":
    unittest.main()
