import unittest
from pathlib import Path

from eqgps.parser import parse_player_name_from_log_path, is_character_who_line, parse_who_zone_count_line


class WhoZoneInferenceTests(unittest.TestCase):
    def test_parse_player_name_from_log_path(self):
        path = Path(r"C:\Users\Public\EQ_P99\Logs\eqlog_Nanantwo_P1999Green 20260604day.txt")
        self.assertEqual(parse_player_name_from_log_path(path), "Nanantwo")

    def test_is_character_who_line_matches_exact_character_entry(self):
        line = "[Mon Apr 27 21:19:59 2026] [5 Bard] Nanantwo (Wood Elf) LFG"
        self.assertTrue(is_character_who_line(line, "Nanantwo"))
        self.assertFalse(is_character_who_line(line, "Nanan"))

    def test_parse_who_zone_count_line_extracts_zone_name(self):
        line = "[Mon Apr 27 21:19:59 2026] There are 4 players in Steamfont Mountains."
        self.assertEqual(parse_who_zone_count_line(line), "Steamfont Mountains")

    def test_parse_who_zone_count_line_handles_singular_player(self):
        line = "[Mon Apr 27 21:19:59 2026] There is 1 player in Estate of Unrest."
        self.assertEqual(parse_who_zone_count_line(line), "Estate of Unrest")

    def test_parse_who_zone_count_ignores_global_everquest_count(self):
        line = "[Mon Apr 27 21:23:33 2026] There are 8 players in EverQuest."
        self.assertIsNone(parse_who_zone_count_line(line))


if __name__ == "__main__":
    unittest.main()
