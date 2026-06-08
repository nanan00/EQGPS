import os
import tempfile
import unittest
from pathlib import Path

from eqgps.app import EQGPSApp
from eqgps.ui_layout import clamp_map_sash_position


class TemporaryAppDataMixin:
    def setUp(self):
        self._old_appdata = os.environ.get("APPDATA")
        self._tmpdir = tempfile.TemporaryDirectory()
        appdata = Path(self._tmpdir.name) / "appdata"
        (appdata / "EQGPS").mkdir(parents=True)
        os.environ["APPDATA"] = str(appdata)

    def tearDown(self):
        if self._old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old_appdata
        self._tmpdir.cleanup()


class SidePanelLayoutTests(TemporaryAppDataMixin, unittest.TestCase):
    def test_peekaboo_strip_stays_narrow_after_map_sash_is_dragged_back_left(self):
        app = None
        try:
            app = EQGPSApp()
            app.geometry("1200x820")
            app.update_idletasks()
            app.update()

            pane = app.main_pane
            pane.sashpos(0, 1050)
            app.update_idletasks()
            app.update()
            pane.sashpos(0, 700)
            app.update_idletasks()
            app.update()

            toggle_width = app.side_toggle_button.master.winfo_width()
            side_width = app.side_panel.winfo_width()
            self.assertLessEqual(toggle_width, 40)
            self.assertGreaterEqual(side_width, 250)
        finally:
            if app is not None:
                app.destroy()

    def test_map_sash_position_is_clamped_to_keep_side_panel_usable(self):
        self.assertEqual(clamp_map_sash_position(total_width=1200, requested_sash=1190, side_min_width=180), 1020)
        self.assertEqual(clamp_map_sash_position(total_width=1200, requested_sash=700, side_min_width=180), 700)
        self.assertEqual(clamp_map_sash_position(total_width=1200, requested_sash=-25, side_min_width=180), 0)


if __name__ == "__main__":
    unittest.main()
