import datetime as dt
import tempfile
import unittest
from pathlib import Path

from eqgps.log_prune import FOUR_MB, maybe_prune_log, prune_archive_path


class LogPruneTests(unittest.TestCase):
    def test_prune_archive_path_appends_iso_timestamp_to_log_name(self):
        timestamp = dt.datetime(2026, 6, 5, 14, 30, 0)
        path = Path(r"C:/logs/eqlog_Nanantwo_P1999Green.txt")

        archive = prune_archive_path(path, timestamp)

        self.assertEqual(archive.name, "eqlog_Nanantwo_P1999Green.txt.2026-06-05T14-30-00")

    def test_maybe_prune_log_archives_and_truncates_logs_over_four_mb(self):
        timestamp = dt.datetime(2026, 6, 5, 14, 30, 0)
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "eqlog_Test_P1999Green.txt"
            content = b"x" * (FOUR_MB + 1)
            log_path.write_bytes(content)

            result = maybe_prune_log(log_path, now=timestamp)

            self.assertTrue(result.pruned)
            self.assertEqual(result.archive_path, log_path.with_name("eqlog_Test_P1999Green.txt.2026-06-05T14-30-00"))
            self.assertEqual(result.archive_path.read_bytes(), content)
            self.assertEqual(log_path.read_bytes(), b"")

    def test_maybe_prune_log_leaves_small_logs_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "eqlog_Test_P1999Green.txt"
            log_path.write_text("small log", encoding="utf-8")

            result = maybe_prune_log(log_path, now=dt.datetime(2026, 6, 5, 14, 30, 0))

            self.assertFalse(result.pruned)
            self.assertIsNone(result.archive_path)
            self.assertEqual(log_path.read_text(encoding="utf-8"), "small log")


if __name__ == "__main__":
    unittest.main()
