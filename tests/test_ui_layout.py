import unittest

from eqgps.ui_layout import (
    chrome_opacity_status_text,
    chrome_opacity_stipple,
    compact_layer_row_padding,
    compact_slider_length,
    keyboard_shortcuts,
    normalize_chrome_opacity,
    overlay_tray_controls,
    side_panel_scroll_units,
    window_alpha_for_chrome_opacity,
    side_panel_toggle_text,
    side_tray_toolbar_buttons,
)


class UiLayoutTests(unittest.TestCase):
    def test_compact_slider_length_is_about_half_of_previous_width(self):
        self.assertEqual(compact_slider_length(previous_length=120), 60)
        self.assertEqual(compact_slider_length(previous_length=85), 42)

    def test_compact_layer_row_padding_reduces_vertical_spacing(self):
        self.assertEqual(compact_layer_row_padding(previous_padding=4), 2)
        self.assertEqual(compact_layer_row_padding(previous_padding=3), 1)

    def test_side_panel_scroll_units_supports_mouse_wheel_and_linux_buttons(self):
        self.assertEqual(side_panel_scroll_units(delta=120), -1)
        self.assertEqual(side_panel_scroll_units(delta=-240), 2)
        self.assertEqual(side_panel_scroll_units(delta=0, button_number=4), -1)
        self.assertEqual(side_panel_scroll_units(delta=0, button_number=5), 1)
        self.assertEqual(side_panel_scroll_units(delta=0, button_number=1), 0)

    def test_side_panel_toggle_text_points_toward_resulting_state(self):
        self.assertEqual(side_panel_toggle_text(is_visible=True), ">")
        self.assertEqual(side_panel_toggle_text(is_visible=False), "<")

    def test_side_tray_toolbar_buttons_are_top_controls_in_order(self):
        self.assertEqual(
            side_tray_toolbar_buttons(),
            ["Open Log", "Auto Log", "Reload Keys", "Fit Map", "Center Player", "Reset Cal"],
        )

    def test_keyboard_shortcuts_describe_common_actions(self):
        shortcuts = keyboard_shortcuts()
        self.assertEqual(shortcuts["Fit Map"], "F")
        self.assertEqual(shortcuts["Center Player"], "C")
        self.assertEqual(shortcuts["Clear Waypoint"], "W")
        self.assertEqual(shortcuts["Toggle Side Tray"], "T")

    def test_normalize_chrome_opacity_clamps_to_slider_range(self):
        self.assertEqual(normalize_chrome_opacity(-10), 0)
        self.assertEqual(normalize_chrome_opacity(45.7), 46)
        self.assertEqual(normalize_chrome_opacity(250), 100)
        self.assertEqual(normalize_chrome_opacity("bad", fallback=75), 75)

    def test_chrome_opacity_status_text_describes_transparent_to_normal_range(self):
        self.assertEqual(chrome_opacity_status_text(0), "Window/UI: 100% transparent")
        self.assertEqual(chrome_opacity_status_text(100), "Window/UI: normal")
        self.assertEqual(chrome_opacity_status_text(25), "Window/UI: 75% transparent")

    def test_chrome_opacity_stipple_maps_slider_to_transparent_hatch_density(self):
        self.assertIsNone(chrome_opacity_stipple(0))
        self.assertEqual(chrome_opacity_stipple(12), "gray12")
        self.assertEqual(chrome_opacity_stipple(25), "gray25")
        self.assertEqual(chrome_opacity_stipple(50), "gray50")
        self.assertEqual(chrome_opacity_stipple(75), "gray75")
        self.assertIsNone(chrome_opacity_stipple(100))

    def test_window_alpha_follows_ui_chrome_slider_only_in_transparency_mode(self):
        self.assertEqual(window_alpha_for_chrome_opacity(0, transparency_enabled=True), 0.0)
        self.assertEqual(window_alpha_for_chrome_opacity(25, transparency_enabled=True), 0.25)
        self.assertEqual(window_alpha_for_chrome_opacity(100, transparency_enabled=True), 1.0)
        self.assertEqual(window_alpha_for_chrome_opacity(25, transparency_enabled=False), 1.0)

    def test_borderless_overlay_keeps_window_alpha_opaque_so_map_does_not_fade(self):
        self.assertEqual(
            window_alpha_for_chrome_opacity(25, transparency_enabled=True, borderless_overlay_enabled=True),
            1.0,
        )

    def test_overlay_tray_controls_include_restore_and_overlay_options(self):
        self.assertEqual(
            overlay_tray_controls(),
            [
                "Restore Normal",
                "Transparency",
                "Opacity Slider",
                "Click Through",
                "Lock Window",
                "Always on Top",
            ],
        )


if __name__ == "__main__":
    unittest.main()
