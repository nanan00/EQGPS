import tempfile
import unittest
import zipfile
from pathlib import Path

from eqgps.map_loader import ensure_map_files_available


class MapAssetsTests(unittest.TestCase):
    def test_ensure_map_files_available_extracts_bundled_zip_when_maps_are_absent(self):
        with tempfile.TemporaryDirectory() as td:
            map_dir = Path(td) / "map_files"
            map_dir.mkdir()
            archive = map_dir / "map_files.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("map_keys.ini", "cabilis west = cabwest\n")
                zf.writestr("map_keys_who.ini", "west cabilis = cabilis west\n")
                zf.writestr("cabwest.txt", "L 0, 0, 0, 1, 1, 0, 255, 255, 255\n")

            self.assertTrue(ensure_map_files_available(map_dir))
            self.assertEqual((map_dir / "map_keys.ini").read_text(encoding="utf-8"), "cabilis west = cabwest\n")
            self.assertTrue((map_dir / "map_keys_who.ini").exists())
            self.assertTrue((map_dir / "cabwest.txt").exists())


if __name__ == "__main__":
    unittest.main()
