import unittest

from eqgps.parser import Loc
from eqgps.runtime_state import RuntimeState


class RuntimeStateTests(unittest.TestCase):
    def test_zone_change_clears_previous_zone_location(self):
        state = RuntimeState()
        state.update_loc(Loc(-1315.95, 794.10, 3.13))

        state.update_zone("North Freeport", "freportn")

        self.assertEqual(state.current_zone_name, "North Freeport")
        self.assertEqual(state.current_zone_key, "freportn")
        self.assertIsNone(state.current_loc)

    def test_loc_after_zone_change_becomes_current_location(self):
        state = RuntimeState()
        state.update_zone("North Freeport", "freportn")
        loc = Loc(-377.17, 582.71, -10.87)

        state.update_loc(loc)

        self.assertEqual(state.current_loc, loc)

    def test_reset_clears_all_fields(self):
        state = RuntimeState()
        state.update_zone("North Freeport", "freportn")
        state.update_loc(Loc(1.0, 2.0, 3.0))

        state.reset()

        self.assertIsNone(state.current_zone_name)
        self.assertIsNone(state.current_zone_key)
        self.assertIsNone(state.current_loc)


if __name__ == "__main__":
    unittest.main()
