import tempfile
import unittest
from pathlib import Path

from eqgps.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_always_on_top_defaults_false_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)

            self.assertFalse(settings.always_on_top)

            settings.always_on_top = True
            reloaded = Settings(settings_path)
            self.assertTrue(reloaded.always_on_top)

            reloaded.always_on_top = False
            self.assertFalse(Settings(settings_path).always_on_top)

    def test_mini_mode_defaults_false_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)

            self.assertFalse(settings.mini_mode)

            settings.mini_mode = True
            reloaded = Settings(settings_path)
            self.assertTrue(reloaded.mini_mode)

            reloaded.mini_mode = False
            self.assertFalse(Settings(settings_path).mini_mode)

    def test_transparency_mode_and_chrome_opacity_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)

            self.assertFalse(settings.transparency_mode)
            self.assertEqual(settings.ui_chrome_opacity, 100)

            settings.transparency_mode = True
            settings.ui_chrome_opacity = 0
            reloaded = Settings(settings_path)
            self.assertTrue(reloaded.transparency_mode)
            self.assertEqual(reloaded.ui_chrome_opacity, 0)

            reloaded.ui_chrome_opacity = 150
            self.assertEqual(Settings(settings_path).ui_chrome_opacity, 100)

            reloaded.ui_chrome_opacity = -20
            self.assertEqual(Settings(settings_path).ui_chrome_opacity, 0)

    def test_borderless_overlay_tray_options_default_false_and_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)

            self.assertFalse(settings.borderless_overlay_mode)
            self.assertFalse(settings.overlay_click_through)
            self.assertFalse(settings.overlay_lock_window)

            settings.borderless_overlay_mode = True
            settings.overlay_click_through = True
            settings.overlay_lock_window = True
            reloaded = Settings(settings_path)

            self.assertTrue(reloaded.borderless_overlay_mode)
            self.assertTrue(reloaded.overlay_click_through)
            self.assertTrue(reloaded.overlay_lock_window)

            reloaded.borderless_overlay_mode = False
            reloaded.overlay_click_through = False
            reloaded.overlay_lock_window = False
            final = Settings(settings_path)

            self.assertFalse(final.borderless_overlay_mode)
            self.assertFalse(final.overlay_click_through)
            self.assertFalse(final.overlay_lock_window)

    def test_corrupt_saved_zone_calibration_values_fall_back_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(
                '{"zone_calibrations": {"freportw": {"offset_x": "bad", "offset_y": null}}}',
                encoding="utf-8",
            )

            settings = Settings(settings_path)

            self.assertEqual(settings.get_zone_calibration("freportw"), {"offset_x": 0.0, "offset_y": 0.0})

    def test_marker_timer_seconds_persists_and_migrates_legacy_minutes(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings = Settings(settings_path)

            settings.set_marker_timer_seconds(90)
            reloaded = Settings(settings_path)
            self.assertEqual(reloaded.get_marker_timer_seconds(), 90)
            self.assertEqual(reloaded.get_marker_timer_minutes(), 2)

            legacy_path = Path(tmp) / "legacy_settings.json"
            legacy_path.write_text('{"marker_timer_minutes": 14}', encoding="utf-8")
            legacy = Settings(legacy_path)
            self.assertEqual(legacy.get_marker_timer_seconds(), 14 * 60)


if __name__ == "__main__":
    unittest.main()
