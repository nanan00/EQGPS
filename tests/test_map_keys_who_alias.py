import tempfile
import textwrap
import unittest
from pathlib import Path

from eqgps.map_keys import MapKeys


class MapKeysWhoAliasTests(unittest.TestCase):
    def test_resolve_uses_who_alias_file_before_main_map_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "map_keys.ini"
            who = tmp_path / "map_keys_who.ini"
            main.write_text(
                textwrap.dedent(
                    """
                    northern desert of ro = nro
                    southern desert of ro = sro
                    """
                ),
                encoding="utf-8",
            )
            who.write_text("north ro = northern desert of ro\n", encoding="utf-8")

            keys = MapKeys.load(main, who)

            self.assertEqual(keys.resolve("north ro"), "nro")
            self.assertEqual(keys.resolve("northern desert of ro"), "nro")

    def test_missing_who_alias_file_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            main = tmp_path / "map_keys.ini"
            main.write_text("northern desert of ro = nro\n", encoding="utf-8")

            keys = MapKeys.load(main, tmp_path / "missing.ini")

            self.assertEqual(keys.resolve("northern desert of ro"), "nro")

    def test_project_map_keys_include_freeport_zones(self):
        map_dir = Path(__file__).resolve().parents[1] / "map_files"
        keys = MapKeys.load(map_dir / "map_keys.ini", map_dir / "map_keys_who.ini")

        self.assertEqual(keys.resolve("West Freeport"), "freportw")
        self.assertEqual(keys.resolve('"West Freeport"'), "freportw")
        self.assertEqual(keys.resolve("North Freeport"), "freportn")
        self.assertEqual(keys.resolve("East Freeport"), "freporte")


if __name__ == "__main__":
    unittest.main()
