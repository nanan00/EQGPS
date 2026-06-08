import datetime as dt
import tempfile
import unittest
from pathlib import Path

from eqgps.log_discovery import discover_recent_logs, is_log_stale, latest_active_log


class LogDiscoveryTests(unittest.TestCase):
    def test_latest_active_log_chooses_newest_eqlog_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            older = log_dir / "eqlog_Older_P1999Green.txt"
            newer = log_dir / "eqlog_Newer_P1999Green.txt"
            ignored = log_dir / "notes.txt"
            older.write_text("old", encoding="utf-8")
            newer.write_text("new", encoding="utf-8")
            ignored.write_text("ignore", encoding="utf-8")
            older_time = dt.datetime(2026, 6, 5, 12, 0, 0).timestamp()
            newer_time = dt.datetime(2026, 6, 5, 13, 0, 0).timestamp()
            ignored_time = dt.datetime(2026, 6, 5, 14, 0, 0).timestamp()
            older.touch()
            newer.touch()
            ignored.touch()
            import os
            os.utime(older, (older_time, older_time))
            os.utime(newer, (newer_time, newer_time))
            os.utime(ignored, (ignored_time, ignored_time))

            self.assertEqual(latest_active_log(log_dir), newer)
            self.assertEqual(discover_recent_logs(log_dir), [newer, older])

    def test_is_log_stale_uses_modified_time_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "eqlog_Test_P1999Green.txt"
            log_path.write_text("log", encoding="utf-8")
            modified = dt.datetime(2026, 6, 5, 12, 0, 0).timestamp()
            import os
            os.utime(log_path, (modified, modified))

            now = dt.datetime(2026, 6, 5, 12, 6, 0).timestamp()
            self.assertTrue(is_log_stale(log_path, now=now, stale_after_seconds=300))
            self.assertFalse(is_log_stale(log_path, now=now, stale_after_seconds=600))
            self.assertTrue(is_log_stale(Path(tmp) / "missing.txt", now=now))


if __name__ == "__main__":
    unittest.main()
