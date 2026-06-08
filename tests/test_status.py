import unittest

from eqgps.calibration import ZoneCalibration
from eqgps.elevation import ElevationFilter
from eqgps.markers import Marker
from eqgps.parser import Loc
from eqgps.status import StatusSnapshot, format_bottom_status


class StatusFormattingTests(unittest.TestCase):
    def test_bottom_status_formats_player_cursor_waypoint_elevation_and_calibration(self):
        waypoint = Marker(zone_key="ecommons", x=10.0, y=20.0, label="Orc Camp", category="Spawn")
        snapshot = StatusSnapshot(
            prefix="Watching log",
            zone_name="East Commonlands",
            zone_key="ecommons",
            current_loc=Loc(20.0, -10.0, 3.0),
            cursor_world=(13.0, 24.0),
            layer_count=2,
            waypoint=waypoint,
            elevation=ElevationFilter(enabled=True, above=75.0, below=25.0),
            calibration=ZoneCalibration(offset_x=4.0, offset_y=-8.0),
            log_path="C:/logs/eqlog_Test.txt",
        )

        self.assertEqual(snapshot.status_text, "Watching log")
        self.assertEqual(
            format_bottom_status(snapshot),
            "Zone: East Commonlands [ecommons] | Player: 20.00, -10.00, 3.00 | "
            "Cursor: 24.0, -13.0 | Dist: 5.0 | Waypoint: Orc Camp (0.0) | "
            "Layers: 2 | Elev: -25/+75 | Cal: 4,-8 | Log: C:/logs/eqlog_Test.txt",
        )

    def test_bottom_status_uses_safe_defaults_when_values_are_missing(self):
        snapshot = StatusSnapshot(
            prefix="No map loaded",
            zone_name=None,
            zone_key=None,
            current_loc=None,
            cursor_world=None,
            layer_count=0,
            waypoint=None,
            elevation=ElevationFilter(),
            calibration=ZoneCalibration(),
            log_path="",
        )

        self.assertEqual(
            format_bottom_status(snapshot),
            "Zone: unknown [unresolved] | Player: none | Cursor: none | Dist: none | "
            "Waypoint: none | Layers: 0 | Elev: off | Cal: 0,0 | Log: ",
        )


if __name__ == "__main__":
    unittest.main()
