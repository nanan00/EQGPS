import tempfile
import unittest
from pathlib import Path

from eqgps.log_prune import FOUR_MB, read_log_then_maybe_prune_log, scan_existing_then_maybe_prune_log
from eqgps.log_watcher import LogTailer


class LogOpenSequenceTests(unittest.TestCase):
    def test_large_existing_log_is_scanned_before_it_is_pruned(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "eqlog_Test_P1999Green.txt"
            log_path.write_bytes(
                b"x" * (FOUR_MB + 1)
                + b"\nYou have entered East Commonlands.\n"
                + b"Your Location is 1, 2, 3\n"
            )
            zones: list[str] = []
            locs = []
            tailer = LogTailer(log_path, zones.append, locs.append)

            result = scan_existing_then_maybe_prune_log(log_path, tailer.scan_existing)

            self.assertTrue(result.pruned)
            self.assertEqual(zones, ["East Commonlands"])
            self.assertEqual((locs[-1].x, locs[-1].y, locs[-1].z), (1.0, 2.0, 3.0))
            self.assertEqual(log_path.read_bytes(), b"")

    def test_large_grown_log_is_polled_before_it_is_pruned(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "eqlog_Test_P1999Green.txt"
            log_path.write_text("already read\n", encoding="utf-8")
            zones: list[str] = []
            locs = []
            tailer = LogTailer(log_path, zones.append, locs.append)
            tailer.scan_existing()
            log_path.write_bytes(
                log_path.read_bytes()
                + b"x" * (FOUR_MB + 1)
                + b"\nYou have entered East Commonlands.\n"
                + b"Your Location is 4, 5, 6\n"
            )

            result = read_log_then_maybe_prune_log(log_path, tailer.poll_new_lines)

            self.assertTrue(result.pruned)
            self.assertEqual(zones, ["East Commonlands"])
            self.assertEqual((locs[-1].x, locs[-1].y, locs[-1].z), (4.0, 5.0, 6.0))
            self.assertEqual(log_path.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
