import json
import tempfile
import unittest
from pathlib import Path

from eqgps.settings import Settings


class SettingsDurabilityTests(unittest.TestCase):
    def test_save_is_atomic_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)
            settings.always_on_top = True

            self.assertTrue(settings_path.exists())
            # The temp file used for the atomic replace must not linger.
            self.assertFalse((settings_path.with_name(settings_path.name + ".tmp")).exists())
            self.assertTrue(json.loads(settings_path.read_text(encoding="utf-8"))["always_on_top"])

    def test_corrupt_settings_are_backed_up_not_silently_wiped(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text("{ this is not valid json", encoding="utf-8")

            settings = Settings(settings_path)

            self.assertEqual(settings.data, {})
            backup = settings_path.with_name(settings_path.name + ".corrupt")
            self.assertTrue(backup.exists())
            self.assertIn("not valid json", backup.read_text(encoding="utf-8"))

    def test_deferred_save_coalesces_writes_until_flush(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)
            settings.flush()  # nothing staged yet; should be a no-op

            settings.begin_deferred_save()
            settings.data["ui_chrome_opacity"] = 50
            settings.save()
            settings.data["ui_chrome_opacity"] = 60
            settings.save()

            # Nothing should be on disk yet while deferral is active.
            self.assertFalse(settings_path.exists())

            settings.flush()

            self.assertTrue(settings_path.exists())
            self.assertEqual(
                json.loads(settings_path.read_text(encoding="utf-8"))["ui_chrome_opacity"],
                60,
            )

    def test_flush_without_pending_change_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)
            settings.begin_deferred_save()
            settings.flush()
            # No save() was called during deferral, so no file should appear.
            self.assertFalse(settings_path.exists())


if __name__ == "__main__":
    unittest.main()
