import unittest

from eqgps.calibration import ZoneCalibration, apply_calibration_to_bounds


class ZoneCalibrationTests(unittest.TestCase):
    def test_calibration_offsets_map_bounds_without_changing_size(self):
        bounds = (-100.0, -50.0, 300.0, 150.0)
        calibration = ZoneCalibration(offset_x=25.0, offset_y=-75.0)

        self.assertEqual(apply_calibration_to_bounds(bounds, calibration), (-75.0, -125.0, 325.0, 75.0))

    def test_nudge_returns_new_calibration(self):
        calibration = ZoneCalibration(offset_x=10.0, offset_y=20.0)

        nudged = calibration.nudged(dx=-5.0, dy=15.0)

        self.assertEqual(nudged.offset_x, 5.0)
        self.assertEqual(nudged.offset_y, 35.0)

    def test_corrupt_saved_calibration_offsets_fall_back_to_zero(self):
        calibration = ZoneCalibration.from_dict({"offset_x": "not numeric", "offset_y": None})

        self.assertEqual(calibration.offset_x, 0.0)
        self.assertEqual(calibration.offset_y, 0.0)


if __name__ == "__main__":
    unittest.main()
