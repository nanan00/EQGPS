import tempfile
import textwrap
import unittest
from pathlib import Path

from eqgps.parser import parse_zone_line, parse_loc_line
from eqgps.map_keys import MapKeys
from eqgps.map_loader import discover_zone_layers, parse_map_file


class Phase1Tests(unittest.TestCase):
    def test_parse_zone_line_extracts_zone_name_with_log_timestamp(self):
        line = "[Thu Jun 04 17:25:13 2026] You have entered Oasis of Marr."
        self.assertEqual(parse_zone_line(line), "Oasis of Marr")

    def test_parse_zone_line_strips_quoted_zone_names(self):
        line = '[Fri Jun 05 00:00:00 2026] You have entered "West Freeport".'
        self.assertEqual(parse_zone_line(line), "West Freeport")

    def test_parse_zone_line_ignores_pvp_area_notification(self):
        line = "[Wed Jun 10 22:29:51 2026] You have entered an Arena (PvP) area."
        self.assertIsNone(parse_zone_line(line))

    def test_parse_loc_line_extracts_three_float_values(self):
        line = "[Mon Apr 27 21:30:42 2026] Your Location is 444.48, 134.01, -124.57"
        loc = parse_loc_line(line)
        self.assertEqual(loc.x, 444.48)
        self.assertEqual(loc.y, 134.01)
        self.assertEqual(loc.z, -124.57)

    def test_map_keys_resolves_zone_name_case_insensitively(self):
        with tempfile.TemporaryDirectory() as td:
            ini = Path(td) / "map_keys.ini"
            ini.write_text("east commonlands = ecommons\nAk'Anon = akanon\n", encoding="utf-8")
            keys = MapKeys.load(ini)
            self.assertEqual(keys.resolve("East Commonlands"), "ecommons")
            self.assertEqual(keys.resolve("ak'anon"), "akanon")

    def test_discover_zone_layers_finds_base_and_numbered_layers_case_insensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "unrest.txt").write_text("", encoding="utf-8")
            (root / "Unrest_1.txt").write_text("", encoding="utf-8")
            (root / "unrest_2.txt").write_text("", encoding="utf-8")
            (root / "other.txt").write_text("", encoding="utf-8")
            layers = discover_zone_layers(root, "unrest")
            self.assertEqual([layer.name for layer in layers], ["unrest", "Unrest_1", "unrest_2"])

    def test_parse_map_file_reads_lines_and_brightens_black(self):
        with tempfile.TemporaryDirectory() as td:
            map_file = Path(td) / "zone.txt"
            map_file.write_text(
                textwrap.dedent(
                    """
                    L -1, -2, 0, 3, 4, 0, 0, 0, 0
                    L 1, 2, 0, 3, 4, 0, 255, 0, 128
                    P 10, 20, 0, 0, 0, 0, Label Here
                    """
                ).strip(),
                encoding="utf-8",
            )
            parsed = parse_map_file(map_file)
            self.assertEqual(len(parsed.lines), 2)
            self.assertEqual(parsed.lines[0].color, (220, 220, 220))
            self.assertEqual(parsed.lines[1].color, (255, 0, 128))
            self.assertEqual(parsed.labels[0].text, "Label Here")
            self.assertEqual(parsed.labels[0].color, (220, 220, 220))


if __name__ == "__main__":
    unittest.main()
