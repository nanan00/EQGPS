import json
import os
import tempfile
import unittest
from pathlib import Path

from eqgps.app import EQGPSApp


class CountingStartupApp(EQGPSApp):
    def __init__(self):
        self.render_count = 0
        super().__init__()

    def render(self) -> None:
        self.render_count += 1


class StartupPerformanceTests(unittest.TestCase):
    def test_startup_scan_coalesces_rendering_for_existing_loc_spam(self):
        old_appdata = os.environ.get("APPDATA")
        with tempfile.TemporaryDirectory() as tmp:
            appdata = Path(tmp) / "appdata"
            settings_dir = appdata / "EQGPS"
            settings_dir.mkdir(parents=True)
            log_path = Path(tmp) / "eqlog_Test_P1999Green.txt"
            log_path.write_text("".join("Your Location is 1, 2, 3\n" for _ in range(50)), encoding="utf-8")
            (settings_dir / "settings.json").write_text(json.dumps({"last_log_path": str(log_path)}), encoding="utf-8")
            os.environ["APPDATA"] = str(appdata)
            app = None
            try:
                app = CountingStartupApp()
                self.assertLessEqual(app.render_count, 5)
                self.assertEqual(app.current_loc.x, 1.0)
            finally:
                if app is not None:
                    app.destroy()
                if old_appdata is None:
                    os.environ.pop("APPDATA", None)
                else:
                    os.environ["APPDATA"] = old_appdata


if __name__ == "__main__":
    unittest.main()
