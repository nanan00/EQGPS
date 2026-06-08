from __future__ import annotations


def compact_slider_length(previous_length: int = 120) -> int:
    return max(24, int(previous_length * 0.5))


def compact_layer_row_padding(previous_padding: int = 3) -> int:
    return max(0, int(previous_padding * 0.5))


def clamp_map_sash_position(total_width: int, requested_sash: int, side_min_width: int = 180) -> int:
    """Keep the map/side-panel sash inside a usable range.

    Tk's ttk.PanedWindow does not support a pane minsize option. Clamp the
    divider manually so the map cannot eat the side tray until text/buttons
    collapse or the peekaboo control disappears.
    """
    usable_total = max(0, int(total_width))
    minimum_side = max(0, int(side_min_width))
    requested = max(0, int(requested_sash))
    max_sash = max(0, usable_total - minimum_side)
    return min(requested, max_sash)


def side_panel_toggle_text(is_visible: bool) -> str:
    return ">" if is_visible else "<"


def side_panel_scroll_units(delta: int = 0, button_number: int | None = None) -> int:
    if button_number == 4:
        return -1
    if button_number == 5:
        return 1
    if delta == 0:
        return 0
    units = int(delta / 120)
    if units == 0:
        units = 1 if delta > 0 else -1
    return -units


def side_tray_toolbar_buttons() -> list[str]:
    return ["Open Log", "Auto Log", "Reload Keys", "Fit Map", "Center Player", "Reset Cal"]


def keyboard_shortcuts() -> dict[str, str]:
    return {
        "Fit Map": "F",
        "Center Player": "C",
        "Clear Waypoint": "W",
        "Toggle Side Tray": "T",
    }


def normalize_chrome_opacity(value: object, fallback: int = 100) -> int:
    try:
        opacity = int(round(float(value)))
    except (TypeError, ValueError):
        opacity = int(fallback)
    return max(0, min(100, opacity))


def chrome_opacity_status_text(opacity: object) -> str:
    normalized = normalize_chrome_opacity(opacity)
    if normalized >= 100:
        return "Window/UI: normal"
    return f"Window/UI: {100 - normalized}% transparent"


def chrome_opacity_stipple(opacity: object) -> str | None:
    normalized = normalize_chrome_opacity(opacity)
    if normalized <= 0 or normalized >= 100:
        return None
    if normalized < 19:
        return "gray12"
    if normalized < 38:
        return "gray25"
    if normalized < 63:
        return "gray50"
    return "gray75"


def window_alpha_for_chrome_opacity(
    opacity: object,
    transparency_enabled: bool,
    borderless_overlay_enabled: bool = False,
) -> float:
    if borderless_overlay_enabled or not transparency_enabled:
        return 1.0
    return normalize_chrome_opacity(opacity) / 100.0


def overlay_tray_controls() -> list[str]:
    return [
        "Restore Normal",
        "Transparency",
        "Opacity Slider",
        "Click Through",
        "Lock Window",
        "Always on Top",
    ]
