from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .calibration import ZoneCalibration, apply_calibration_to_bounds
from .coordinates import MapPoint, loc_to_map_point, map_point_to_loc_xy
from .elevation import ElevationFilter, label_visible_at_player_z, line_visible_at_player_z
from .heading import HeadingTracker
from .log_discovery import DEFAULT_STALE_SECONDS, is_log_stale, latest_active_log
from .log_polling import read_then_prune_safely
from .log_prune import maybe_prune_log
from .log_watcher import LogTailer
from .map_keys import MapKeys
from .map_loader import MapLayer, ParsedMap, discover_zone_layers, ensure_map_files_available, parse_map_file
from .markers import (
    DEFAULT_TIMER_SECONDS,
    Marker,
    MarkerStore,
    clear_marker_timer,
    format_timer_duration,
    marker_timer_state,
    normalize_timer_seconds,
    reset_marker_timer,
    reset_marker_timer_paused,
    update_marker_details,
)
from .parser import Loc
from .runtime_state import RuntimeState
from .settings import Settings
from .status import StatusSnapshot, format_bottom_status
from .timer_sound import TimerSoundNotifier, default_windows_sound_path
from .ui_layout import (
    chrome_opacity_status_text,
    chrome_opacity_stipple,
    clamp_map_sash_position,
    compact_layer_row_padding,
    compact_slider_length,
    keyboard_shortcuts,
    normalize_chrome_opacity,
    overlay_tray_controls,
    side_panel_scroll_units,
    side_panel_toggle_text,
    side_tray_toolbar_buttons,
    window_alpha_for_chrome_opacity,
)
from .viewport import ViewportTransform, clamp_pan_units, fit_viewport_to_bounds


BG = "#101010"
TRANSPARENT_CHROME_COLOR = "#010203"
FG = "#dddddd"
PLAYER_COLOR = "#00ffff"
WAYPOINT_COLOR = "#ffcc00"


def rgb_to_hex(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % color


def blend_with_bg(color: tuple[int, int, int], opacity: int) -> tuple[int, int, int]:
    alpha = max(0, min(100, opacity)) / 100.0
    bg = (16, 16, 16)
    return tuple(int(channel * alpha + bg_channel * (1.0 - alpha)) for channel, bg_channel in zip(color, bg))


@dataclass
class LayerState:
    layer: MapLayer
    parsed: ParsedMap
    visible_var: tk.BooleanVar
    opacity_var: tk.IntVar


class EQGPSApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EQGPS - Phase 18")
        self.geometry(self._initial_geometry())
        self.minsize(800, 500)

        self.settings = Settings()
        self.map_dir = self.settings.map_dir
        ensure_map_files_available(self.map_dir)
        self.map_keys = MapKeys.load(self.map_dir / "map_keys.ini", self.map_dir / "map_keys_who.ini")
        self.current_zone_name: str | None = None
        self.current_zone_key: str | None = None
        self.current_loc: Loc | None = None
        self.state = RuntimeState()
        self.cursor_world: tuple[float, float] | None = None
        self.layer_states: list[LayerState] = []
        self.raw_map_bounds: tuple[float, float, float, float] | None = None
        self.map_bounds: tuple[float, float, float, float] | None = None
        self.current_calibration = ZoneCalibration()
        self.scale = 1.0
        self.offset_x = 30.0
        self.offset_y = 30.0
        self.drag_start: tuple[int, int] | None = None
        self.pending_fit_map = False
        self.heading = HeadingTracker(min_distance=3.0)
        self.marker_store = MarkerStore.from_dict(self.settings.get_marker_data())
        self.marker_search_var: tk.StringVar | None = None
        self.marker_list: tk.Listbox | None = None
        self.marker_list_ids: list[str] = []
        self.marker_timer_text_var: tk.StringVar | None = None
        default_sound = default_windows_sound_path()
        sound_settings = self.settings.get_timer_sound_settings(default_sound)
        self.timer_sound_enabled_var: tk.BooleanVar | None = None
        self.timer_sound_path_var: tk.StringVar | None = None
        self.always_on_top_var: tk.BooleanVar | None = None
        self.mini_mode_var: tk.BooleanVar | None = None
        self.transparency_mode_var: tk.BooleanVar | None = None
        self.ui_chrome_opacity_var: tk.IntVar | None = None
        self.ui_chrome_opacity_status_var: tk.StringVar | None = None
        self.borderless_overlay_var: tk.BooleanVar | None = None
        self.overlay_click_through_var: tk.BooleanVar | None = None
        self.overlay_lock_window_var: tk.BooleanVar | None = None
        self.overlay_tray: tk.Toplevel | None = None
        self.overlay_grip: tk.Frame | None = None
        self.overlay_drag_start: tuple[int, int, int, int] | None = None
        self._batching_log_scan = False
        self.initial_timer_sound_enabled = bool(sound_settings.get("enabled", True))
        self.initial_timer_sound_path = str(sound_settings.get("path") or default_sound)
        self.timer_sound_notifier = TimerSoundNotifier()
        elevation = ElevationFilter.from_dict(self.settings.get_elevation_filter())
        self.elevation_enabled_var: tk.BooleanVar | None = None
        self.elevation_above_var: tk.DoubleVar | None = None
        self.elevation_below_var: tk.DoubleVar | None = None
        self.initial_elevation_filter = elevation
        self.context_world: tuple[float, float] | None = None
        self.context_marker_id: str | None = None
        self.main_pane: ttk.PanedWindow | None = None
        self.map_area: ttk.Frame | None = None
        self.side_panel: ttk.Frame | None = None
        self.side_tray_canvas: tk.Canvas | None = None
        self.side_toggle_button: ttk.Button | None = None
        self.side_panel_visible = True

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.tailer = LogTailer(self.settings.log_path, self.handle_zone, self.handle_loc, self.handle_sense_heading)
        self.open_log_path(self.settings.log_path, scan=True, silent=True)
        self.after(750, self.poll_log)

    def _initial_geometry(self) -> str:
        settings = Settings()
        return settings.window_geometry or "1200x820"

    def _build_ui(self) -> None:
        self.configure(bg=BG)
        self.status_var = tk.StringVar(value="EQGPS starting...")

        self.main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.main_pane.bind("<B1-Motion>", self.enforce_side_panel_min_width, add="+")
        self.main_pane.bind("<ButtonRelease-1>", self.enforce_side_panel_min_width, add="+")

        map_area = ttk.Frame(self.main_pane)
        self.map_area = map_area
        self.canvas = tk.Canvas(map_area, bg=BG, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        toggle_strip = ttk.Frame(map_area, width=18)
        toggle_strip.pack_propagate(False)
        toggle_strip.pack(side=tk.RIGHT, fill=tk.Y)
        self.side_toggle_button = ttk.Button(toggle_strip, text=side_panel_toggle_text(True), width=2, command=self.toggle_side_panel)
        self.side_toggle_button.pack(fill=tk.Y, expand=True)
        self.main_pane.add(map_area, weight=5)

        side_container = ttk.Frame(self.main_pane, width=180)
        self.side_panel = side_container
        self.main_pane.add(side_container, weight=0)

        side_scrollbar = ttk.Scrollbar(side_container, orient=tk.VERTICAL)
        side_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        side_canvas = tk.Canvas(side_container, highlightthickness=0, yscrollcommand=side_scrollbar.set)
        side_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        side_scrollbar.configure(command=side_canvas.yview)
        self.side_tray_canvas = side_canvas

        side = ttk.Frame(side_canvas, width=130)
        side_window = side_canvas.create_window((0, 0), window=side, anchor=tk.NW)
        side.bind("<Configure>", lambda _event: side_canvas.configure(scrollregion=side_canvas.bbox("all")))
        side_canvas.bind("<Configure>", lambda event: side_canvas.itemconfigure(side_window, width=event.width))
        side_canvas.bind("<MouseWheel>", self.on_side_tray_mousewheel)
        side_canvas.bind("<Button-4>", self.on_side_tray_mousewheel)
        side_canvas.bind("<Button-5>", self.on_side_tray_mousewheel)
        side.bind("<MouseWheel>", self.on_side_tray_mousewheel)
        side.bind("<Button-4>", self.on_side_tray_mousewheel)
        side.bind("<Button-5>", self.on_side_tray_mousewheel)

        ttk.Label(side, text="Controls", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 4))
        controls = ttk.Frame(side)
        controls.pack(fill=tk.X, padx=6, pady=(0, 4))
        command_by_label = {
            "Open Log": self.pick_log_file,
            "Auto Log": self.open_latest_active_log,
            "Reload Keys": self.reload_map_keys,
            "Fit Map": self.fit_map,
            "Center Player": self.center_player,
            "Reset Cal": self.reset_zone_calibration,
        }
        for label in side_tray_toolbar_buttons():
            ttk.Button(controls, text=label, command=command_by_label[label]).pack(fill=tk.X, pady=1)
        self.always_on_top_var = tk.BooleanVar(value=self.settings.always_on_top)
        ttk.Checkbutton(controls, text="Always on Top", variable=self.always_on_top_var, command=self.toggle_always_on_top).pack(anchor=tk.W, pady=(3, 1))
        self.mini_mode_var = tk.BooleanVar(value=self.settings.mini_mode)
        ttk.Checkbutton(controls, text="Mini Mode", variable=self.mini_mode_var, command=self.toggle_mini_mode).pack(anchor=tk.W, pady=(1, 1))
        self.transparency_mode_var = tk.BooleanVar(value=self.settings.transparency_mode)
        ttk.Checkbutton(controls, text="Transparent UI", variable=self.transparency_mode_var, command=self.toggle_transparency_mode).pack(anchor=tk.W, pady=(1, 1))
        self.borderless_overlay_var = tk.BooleanVar(value=self.settings.borderless_overlay_mode)
        ttk.Checkbutton(controls, text="Borderless Overlay", variable=self.borderless_overlay_var, command=self.toggle_borderless_overlay_mode).pack(anchor=tk.W, pady=(1, 1))
        self.overlay_click_through_var = tk.BooleanVar(value=self.settings.overlay_click_through)
        self.overlay_lock_window_var = tk.BooleanVar(value=self.settings.overlay_lock_window)
        ttk.Button(controls, text="Overlay Tray", command=self.show_overlay_tray).pack(fill=tk.X, pady=(1, 3))
        self.ui_chrome_opacity_var = tk.IntVar(value=self.settings.ui_chrome_opacity)
        self.ui_chrome_opacity_status_var = tk.StringVar(value=chrome_opacity_status_text(self.ui_chrome_opacity_var.get()))
        ttk.Scale(
            controls,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.ui_chrome_opacity_var,
            length=compact_slider_length(120),
            command=self.on_ui_chrome_opacity_changed,
        ).pack(fill=tk.X, pady=(0, 1))
        ttk.Label(controls, textvariable=self.ui_chrome_opacity_status_var, wraplength=115).pack(anchor=tk.W, pady=(0, 3))
        shortcut_text = "  ".join(f"{key}: {action}" for action, key in keyboard_shortcuts().items())
        ttk.Label(side, text=shortcut_text, wraplength=115).pack(anchor=tk.W, padx=8, pady=(0, 4))
        ttk.Label(side, textvariable=self.status_var, wraplength=115).pack(anchor=tk.W, padx=8, pady=(0, 6))
        ttk.Separator(side, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)

        ttk.Label(side, text="Map Layers", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(4, 4))
        self.layer_frame = ttk.Frame(side)
        self.layer_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        ttk.Separator(side, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)
        ttk.Label(side, text="Elevation", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(4, 2))
        self.elevation_enabled_var = tk.BooleanVar(value=self.initial_elevation_filter.enabled)
        self.elevation_above_var = tk.DoubleVar(value=self.initial_elevation_filter.above)
        self.elevation_below_var = tk.DoubleVar(value=self.initial_elevation_filter.below)
        ttk.Checkbutton(side, text="Filter by /loc Z", variable=self.elevation_enabled_var, command=self.on_elevation_changed).pack(anchor=tk.W, padx=8)
        elev_row = ttk.Frame(side)
        elev_row.pack(fill=tk.X, padx=6, pady=2)
        ttk.Label(elev_row, text="Above").grid(row=0, column=0, sticky=tk.W)
        above_spin = tk.Spinbox(elev_row, from_=0, to=5000, increment=5, width=5, textvariable=self.elevation_above_var, command=self.on_elevation_changed)
        above_spin.grid(row=0, column=1, sticky=tk.EW, padx=2)
        ttk.Label(elev_row, text="Below").grid(row=1, column=0, sticky=tk.W)
        below_spin = tk.Spinbox(elev_row, from_=0, to=5000, increment=5, width=5, textvariable=self.elevation_below_var, command=self.on_elevation_changed)
        below_spin.grid(row=1, column=1, sticky=tk.EW, padx=2)
        elev_row.columnconfigure(1, weight=1)
        above_spin.bind("<FocusOut>", lambda _event: self.on_elevation_changed())
        below_spin.bind("<FocusOut>", lambda _event: self.on_elevation_changed())
        above_spin.bind("<Return>", lambda _event: self.on_elevation_changed())
        below_spin.bind("<Return>", lambda _event: self.on_elevation_changed())

        ttk.Separator(side, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=4)
        ttk.Label(side, text="Markers", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(4, 2))
        self.marker_search_var = tk.StringVar()
        self.marker_search_var.trace_add("write", lambda *_args: self.rebuild_marker_panel())
        ttk.Entry(side, textvariable=self.marker_search_var).pack(fill=tk.X, padx=6, pady=2)
        self.marker_list = tk.Listbox(side, height=6, exportselection=False)
        self.marker_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        self.marker_list.bind("<<ListboxSelect>>", lambda _event: self.select_marker_from_list())
        timer_row = ttk.Frame(side)
        timer_row.pack(fill=tk.X, padx=6, pady=2)
        ttk.Label(timer_row, text="Timer").pack(side=tk.LEFT)
        self.marker_timer_text_var = tk.StringVar(
            value=format_timer_duration(self.settings.get_marker_timer_seconds(DEFAULT_TIMER_SECONDS))
        )
        ttk.Entry(timer_row, width=6, textvariable=self.marker_timer_text_var).pack(side=tk.LEFT, padx=2)
        ttk.Label(timer_row, text="mm:ss").pack(side=tk.LEFT)
        marker_buttons = ttk.Frame(side)
        marker_buttons.pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(marker_buttons, text="WP", command=self.set_selected_marker_waypoint).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(marker_buttons, text="Edit", command=self.edit_selected_marker).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(marker_buttons, text="Start", command=self.start_selected_marker_timer).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(marker_buttons, text="Del", command=self.delete_selected_marker).pack(side=tk.LEFT, expand=True, fill=tk.X)
        timer_buttons = ttk.Frame(side)
        timer_buttons.pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(timer_buttons, text="Reset Timer", command=self.reset_selected_marker_timer).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(timer_buttons, text="Clear Timer", command=self.clear_selected_marker_timer).pack(side=tk.LEFT, expand=True, fill=tk.X)
        import_export = ttk.Frame(side)
        import_export.pack(fill=tk.X, padx=6, pady=2)
        ttk.Button(import_export, text="Import", command=self.import_markers).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(import_export, text="Export", command=self.export_markers).pack(side=tk.LEFT, expand=True, fill=tk.X)
        sound_row = ttk.Frame(side)
        sound_row.pack(fill=tk.X, padx=6, pady=2)
        self.timer_sound_enabled_var = tk.BooleanVar(value=self.initial_timer_sound_enabled)
        self.timer_sound_path_var = tk.StringVar(value=self.initial_timer_sound_path)
        ttk.Checkbutton(sound_row, text="Sound", variable=self.timer_sound_enabled_var, command=self.save_timer_sound_settings).pack(side=tk.LEFT)
        ttk.Button(sound_row, text="Pick", command=self.pick_timer_sound).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(sound_row, text="Test", command=self.test_timer_sound).pack(side=tk.LEFT, expand=True, fill=tk.X)

        ttk.Label(side, text="Wheel zooms; drag pans; right-click map for markers.", wraplength=115).pack(anchor=tk.W, padx=8, pady=8)
        self.bind_side_tray_scroll(side)

        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.on_mousewheel_delta(e, 120))
        self.canvas.bind("<Button-5>", lambda e: self.on_mousewheel_delta(e, -120))
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Leave>", self.on_mouse_leave)
        self.canvas.bind("<Button-3>", self.on_context_menu)
        self.bind("<Control-Up>", lambda _e: self.nudge_zone_calibration(0, 10))
        self.bind("<Control-Down>", lambda _e: self.nudge_zone_calibration(0, -10))
        self.bind("<Control-Left>", lambda _e: self.nudge_zone_calibration(-10, 0))
        self.bind("<Control-Right>", lambda _e: self.nudge_zone_calibration(10, 0))
        self.bind("<Control-Shift-Up>", lambda _e: self.nudge_zone_calibration(0, 100))
        self.bind("<Control-Shift-Down>", lambda _e: self.nudge_zone_calibration(0, -100))
        self.bind("<Control-Shift-Left>", lambda _e: self.nudge_zone_calibration(-100, 0))
        self.bind("<Control-Shift-Right>", lambda _e: self.nudge_zone_calibration(100, 0))
        self.bind_keyboard_shortcuts()
        self.apply_always_on_top()
        self.apply_transparency_mode()

        self.bottom_var = tk.StringVar(value="Log: not opened")
        self.bottom_label = ttk.Label(self, textvariable=self.bottom_var, anchor=tk.W)
        self.bottom_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.apply_mini_mode()
        self.apply_borderless_overlay_mode(show_tray=self.settings.borderless_overlay_mode)
        self.apply_transparency_mode()

    def bind_keyboard_shortcuts(self) -> None:
        bindings = {
            "f": self.fit_map,
            "c": self.center_player,
            "w": self.clear_waypoint,
            "t": self.toggle_side_panel,
        }
        for key, command in bindings.items():
            self.bind(f"<{key}>", lambda event, cmd=command: self.run_keyboard_shortcut(event, cmd))
            self.bind(f"<{key.upper()}>", lambda event, cmd=command: self.run_keyboard_shortcut(event, cmd))

    def run_keyboard_shortcut(self, event: tk.Event, command) -> str | None:
        focus = self.focus_get()
        if focus and focus.winfo_class() in {"Entry", "TEntry", "Spinbox", "TSpinbox", "Listbox"}:
            return None
        command()
        return "break"

    def apply_always_on_top(self) -> None:
        enabled = bool(self.always_on_top_var.get()) if self.always_on_top_var else self.settings.always_on_top
        self.attributes("-topmost", enabled)

    def toggle_always_on_top(self) -> None:
        enabled = bool(self.always_on_top_var.get()) if self.always_on_top_var else False
        self.settings.always_on_top = enabled
        self.apply_always_on_top()
        self.update_status("Always on top enabled" if enabled else "Always on top disabled")

    def is_borderless_overlay_enabled(self) -> bool:
        if self.borderless_overlay_var:
            return bool(self.borderless_overlay_var.get())
        return self.settings.borderless_overlay_mode

    def is_overlay_click_through_enabled(self) -> bool:
        if self.overlay_click_through_var:
            return bool(self.overlay_click_through_var.get())
        return self.settings.overlay_click_through

    def is_overlay_locked(self) -> bool:
        if self.overlay_lock_window_var:
            return bool(self.overlay_lock_window_var.get())
        return self.settings.overlay_lock_window

    def show_overlay_tray(self) -> None:
        if self.overlay_tray and self.overlay_tray.winfo_exists():
            self.overlay_tray.deiconify()
            self.overlay_tray.lift()
            return
        tray = tk.Toplevel(self)
        self.overlay_tray = tray
        tray.title("EQGPS Overlay Tray")
        tray.geometry("230x270")
        tray.attributes("-topmost", True)
        tray.protocol("WM_DELETE_WINDOW", self.hide_overlay_tray)
        tray.configure(bg=BG)

        frame = ttk.Frame(tray, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Overlay Tray", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 4))
        controls = overlay_tray_controls()
        ttk.Button(frame, text=controls[0], command=self.restore_normal_mode).pack(fill=tk.X, pady=(0, 4))
        ttk.Checkbutton(frame, text=controls[1], variable=self.transparency_mode_var, command=self.toggle_transparency_mode).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text="Borderless Overlay", variable=self.borderless_overlay_var, command=self.toggle_borderless_overlay_mode).pack(anchor=tk.W)
        ttk.Label(frame, text=controls[2]).pack(anchor=tk.W, pady=(4, 0))
        ttk.Scale(
            frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.ui_chrome_opacity_var,
            length=180,
            command=self.on_ui_chrome_opacity_changed,
        ).pack(fill=tk.X)
        if self.ui_chrome_opacity_status_var:
            ttk.Label(frame, textvariable=self.ui_chrome_opacity_status_var).pack(anchor=tk.W, pady=(0, 4))
        ttk.Checkbutton(frame, text=controls[3], variable=self.overlay_click_through_var, command=self.toggle_overlay_click_through).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text=controls[4], variable=self.overlay_lock_window_var, command=self.toggle_overlay_lock_window).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text=controls[5], variable=self.always_on_top_var, command=self.toggle_always_on_top).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text="Mini Mode", variable=self.mini_mode_var, command=self.toggle_mini_mode).pack(anchor=tk.W)
        ttk.Button(frame, text="Hide Tray", command=self.hide_overlay_tray).pack(fill=tk.X, pady=(6, 0))

    def hide_overlay_tray(self) -> None:
        if self.overlay_tray and self.overlay_tray.winfo_exists():
            self.overlay_tray.withdraw()

    def current_ui_chrome_opacity(self) -> int:
        if not self.ui_chrome_opacity_var:
            return self.settings.ui_chrome_opacity
        opacity = normalize_chrome_opacity(self.ui_chrome_opacity_var.get())
        self.ui_chrome_opacity_var.set(opacity)
        return opacity

    def current_chrome_background(self) -> str:
        enabled = bool(self.transparency_mode_var.get()) if self.transparency_mode_var else self.settings.transparency_mode
        if not enabled:
            return BG
        opacity = self.current_ui_chrome_opacity()
        if opacity < 100:
            return TRANSPARENT_CHROME_COLOR
        return BG

    def draw_canvas_chrome_background(self) -> None:
        if not self.transparency_mode_var or not self.transparency_mode_var.get():
            return
        opacity = self.current_ui_chrome_opacity()
        if opacity <= 0 or opacity >= 100:
            return
        stipple = chrome_opacity_stipple(opacity)
        self.canvas.create_rectangle(
            0,
            0,
            max(1, self.canvas.winfo_width()),
            max(1, self.canvas.winfo_height()),
            fill=BG,
            outline="",
            stipple=stipple,
        )

    def apply_transparency_mode(self) -> None:
        enabled = bool(self.transparency_mode_var.get()) if self.transparency_mode_var else self.settings.transparency_mode
        overlay_enabled = self.is_borderless_overlay_enabled()
        opacity = self.current_ui_chrome_opacity()
        background = self.current_chrome_background()
        try:
            self.attributes("-transparentcolor", TRANSPARENT_CHROME_COLOR if enabled and opacity < 100 else "")
        except tk.TclError:
            pass
        try:
            self.attributes(
                "-alpha",
                window_alpha_for_chrome_opacity(
                    opacity,
                    transparency_enabled=enabled,
                    borderless_overlay_enabled=overlay_enabled,
                ),
            )
        except tk.TclError:
            pass
        self.configure(bg=background)
        if hasattr(self, "canvas"):
            self.canvas.configure(bg=background)
        if self.side_tray_canvas:
            self.side_tray_canvas.configure(bg=background)
        self.update_overlay_grip()
        if self.ui_chrome_opacity_status_var:
            self.ui_chrome_opacity_status_var.set(chrome_opacity_status_text(opacity))

    def create_overlay_grip(self) -> None:
        if self.overlay_grip and self.overlay_grip.winfo_exists():
            return
        grip = tk.Frame(self, bg=self.current_chrome_background(), bd=1, relief=tk.SOLID)
        label = tk.Label(grip, text="EQGPS drag", bg=self.current_chrome_background(), fg=FG, font=("Segoe UI", 8, "bold"))
        label.pack(side=tk.LEFT, padx=6, pady=2)
        ttk.Button(grip, text="Tray", command=self.show_overlay_tray, width=5).pack(side=tk.LEFT, padx=(0, 2), pady=1)
        for widget in (grip, label):
            widget.bind("<ButtonPress-1>", self.on_overlay_drag_start)
            widget.bind("<B1-Motion>", self.on_overlay_drag)
            widget.bind("<ButtonRelease-1>", self.on_overlay_drag_end)
        self.overlay_grip = grip

    def update_overlay_grip(self) -> None:
        if not self.overlay_grip or not self.overlay_grip.winfo_exists():
            return
        background = self.current_chrome_background()
        self.overlay_grip.configure(bg=background)
        for child in self.overlay_grip.winfo_children():
            try:
                child.configure(bg=background)
            except tk.TclError:
                pass
        if self.is_borderless_overlay_enabled() and not self.is_overlay_click_through_enabled() and not self.is_overlay_locked():
            self.overlay_grip.place(x=8, y=8)
            self.overlay_grip.lift()
        else:
            self.overlay_grip.place_forget()

    def on_overlay_drag_start(self, event: tk.Event) -> str | None:
        if self.is_overlay_locked() or self.is_overlay_click_through_enabled():
            return "break"
        self.overlay_drag_start = (int(event.x_root), int(event.y_root), self.winfo_x(), self.winfo_y())
        return "break"

    def on_overlay_drag(self, event: tk.Event) -> str | None:
        if not self.overlay_drag_start or self.is_overlay_locked() or self.is_overlay_click_through_enabled():
            return "break"
        start_x, start_y, window_x, window_y = self.overlay_drag_start
        dx = int(event.x_root) - start_x
        dy = int(event.y_root) - start_y
        self.geometry(f"+{window_x + dx}+{window_y + dy}")
        return "break"

    def on_overlay_drag_end(self, _event: tk.Event) -> str | None:
        self.overlay_drag_start = None
        return "break"

    def toggle_transparency_mode(self) -> None:
        enabled = bool(self.transparency_mode_var.get()) if self.transparency_mode_var else False
        self.settings.transparency_mode = enabled
        self.apply_transparency_mode()
        self.update_status("Transparent UI enabled" if enabled else "Transparent UI disabled")
        self.render()

    def toggle_borderless_overlay_mode(self) -> None:
        enabled = self.is_borderless_overlay_enabled()
        if enabled and self.transparency_mode_var and not self.transparency_mode_var.get():
            self.transparency_mode_var.set(True)
            self.settings.transparency_mode = True
        self.settings.borderless_overlay_mode = enabled
        self.apply_borderless_overlay_mode(show_tray=enabled)
        self.apply_transparency_mode()
        self.update_status("Borderless overlay enabled" if enabled else "Borderless overlay disabled")
        self.render()

    def apply_borderless_overlay_mode(self, show_tray: bool = False) -> None:
        enabled = self.is_borderless_overlay_enabled()
        if enabled:
            self.create_overlay_grip()
            self.overrideredirect(True)
            if self.main_pane and self.side_panel and self.side_panel_visible:
                self.main_pane.forget(self.side_panel)
                self.side_panel_visible = False
            if hasattr(self, "bottom_label"):
                self.bottom_label.pack_forget()
            if self.side_toggle_button:
                self.side_toggle_button.configure(text=side_panel_toggle_text(False))
            if show_tray:
                self.show_overlay_tray()
        else:
            self.overrideredirect(False)
            self.set_window_click_through(False)
            if self.overlay_grip and self.overlay_grip.winfo_exists():
                self.overlay_grip.place_forget()
            if hasattr(self, "bottom_label") and not self.bottom_label.winfo_ismapped():
                self.bottom_label.pack(side=tk.BOTTOM, fill=tk.X)
            if self.main_pane and self.side_panel and not self.side_panel_visible and not (self.mini_mode_var and self.mini_mode_var.get()):
                self.main_pane.add(self.side_panel, weight=0)
                self.side_panel_visible = True
            if self.side_toggle_button:
                self.side_toggle_button.configure(text=side_panel_toggle_text(self.side_panel_visible))
        self.apply_overlay_click_through()
        self.update_overlay_grip()
        self.apply_always_on_top()

    def restore_normal_mode(self) -> None:
        if self.borderless_overlay_var:
            self.borderless_overlay_var.set(False)
        if self.transparency_mode_var:
            self.transparency_mode_var.set(False)
        if self.overlay_click_through_var:
            self.overlay_click_through_var.set(False)
        if self.overlay_lock_window_var:
            self.overlay_lock_window_var.set(False)
        if self.mini_mode_var:
            self.mini_mode_var.set(False)
        self.settings.borderless_overlay_mode = False
        self.settings.transparency_mode = False
        self.settings.overlay_click_through = False
        self.settings.overlay_lock_window = False
        self.settings.mini_mode = False
        self.apply_borderless_overlay_mode(show_tray=False)
        self.apply_mini_mode()
        self.apply_transparency_mode()
        if self.overlay_tray and self.overlay_tray.winfo_exists():
            self.overlay_tray.withdraw()
        self.update_status("Restored normal window mode")
        self.render()

    def toggle_overlay_click_through(self) -> None:
        enabled = self.is_overlay_click_through_enabled()
        if enabled and self.borderless_overlay_var and not self.borderless_overlay_var.get():
            self.borderless_overlay_var.set(True)
            self.settings.borderless_overlay_mode = True
            if self.transparency_mode_var:
                self.transparency_mode_var.set(True)
                self.settings.transparency_mode = True
            self.apply_borderless_overlay_mode(show_tray=True)
        self.settings.overlay_click_through = enabled
        self.apply_overlay_click_through()
        self.update_overlay_grip()
        self.update_status("Overlay click-through enabled" if enabled else "Overlay click-through disabled")

    def apply_overlay_click_through(self) -> None:
        enabled = self.is_borderless_overlay_enabled() and self.is_overlay_click_through_enabled()
        self.set_window_click_through(enabled)

    def set_window_click_through(self, enabled: bool) -> None:
        try:
            import win32con
            import win32gui
        except ImportError:
            return
        try:
            hwnd = int(self.winfo_id())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if enabled:
                style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            else:
                style &= ~win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            win32gui.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
            )
        except Exception:
            return

    def toggle_overlay_lock_window(self) -> None:
        enabled = self.is_overlay_locked()
        self.settings.overlay_lock_window = enabled
        self.update_overlay_grip()
        self.update_status("Overlay window locked" if enabled else "Overlay window unlocked")

    def on_ui_chrome_opacity_changed(self, _value: str | None = None) -> None:
        opacity = self.current_ui_chrome_opacity()
        self.settings.ui_chrome_opacity = opacity
        self.apply_transparency_mode()
        self.update_status(chrome_opacity_status_text(opacity))
        self.render()

    def apply_mini_mode(self) -> None:
        enabled = bool(self.mini_mode_var.get()) if self.mini_mode_var else self.settings.mini_mode
        overlay_enabled = self.is_borderless_overlay_enabled()
        if enabled or overlay_enabled:
            self.minsize(360, 320)
            if self.main_pane and self.side_panel and self.side_panel_visible:
                self.main_pane.forget(self.side_panel)
                self.side_panel_visible = False
            if hasattr(self, "bottom_label"):
                self.bottom_label.pack_forget()
            if self.side_toggle_button:
                self.side_toggle_button.configure(text=side_panel_toggle_text(False))
            if enabled and not overlay_enabled and (self.winfo_width() > 640 or self.winfo_height() > 640):
                self.geometry("480x480")
        else:
            self.minsize(800, 500)
            if hasattr(self, "bottom_label") and not self.bottom_label.winfo_ismapped():
                self.bottom_label.pack(side=tk.BOTTOM, fill=tk.X)
            if self.main_pane and self.side_panel and not self.side_panel_visible:
                self.main_pane.add(self.side_panel, weight=0)
                self.side_panel_visible = True
            if self.side_toggle_button:
                self.side_toggle_button.configure(text=side_panel_toggle_text(True))
        self.request_fit_map()
        self.render()

    def toggle_mini_mode(self) -> None:
        enabled = bool(self.mini_mode_var.get()) if self.mini_mode_var else False
        self.settings.mini_mode = enabled
        self.apply_mini_mode()
        self.update_status("Mini mode enabled" if enabled else "Mini mode disabled")

    def bind_side_tray_scroll(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self.on_side_tray_mousewheel)
        widget.bind("<Button-4>", self.on_side_tray_mousewheel)
        widget.bind("<Button-5>", self.on_side_tray_mousewheel)
        for child in widget.winfo_children():
            self.bind_side_tray_scroll(child)

    def on_side_tray_mousewheel(self, event: tk.Event) -> str | None:
        if not self.side_tray_canvas:
            return None
        units = side_panel_scroll_units(
            delta=int(getattr(event, "delta", 0) or 0),
            button_number=getattr(event, "num", None),
        )
        if units:
            self.side_tray_canvas.yview_scroll(units, "units")
            return "break"
        return None

    def enforce_side_panel_min_width(self, _event: tk.Event | None = None) -> None:
        if not self.main_pane or not self.side_panel_visible:
            return
        panes = self.main_pane.panes()
        if len(panes) < 2:
            return
        total_width = self.main_pane.winfo_width()
        if total_width <= 1:
            return
        current_sash = self.main_pane.sashpos(0)
        clamped_sash = clamp_map_sash_position(total_width, current_sash, side_min_width=180)
        if clamped_sash != current_sash:
            self.main_pane.sashpos(0, clamped_sash)

    def toggle_side_panel(self) -> None:
        if self.is_borderless_overlay_enabled():
            self.show_overlay_tray()
            return
        if not self.main_pane or not self.side_panel or not self.side_toggle_button:
            return
        if self.side_panel_visible:
            self.main_pane.forget(self.side_panel)
            self.side_panel_visible = False
        else:
            self.main_pane.add(self.side_panel, weight=0)
            self.side_panel_visible = True
            self.after_idle(self.enforce_side_panel_min_width)
        self.side_toggle_button.configure(text=side_panel_toggle_text(self.side_panel_visible))
        self.request_fit_map()
        self.render()

    def prune_log_if_needed(self, path: Path) -> None:
        try:
            result = maybe_prune_log(path)
        except OSError as exc:
            self.update_status(f"Log prune skipped: {exc}")
            return
        if result.pruned:
            if hasattr(self, "tailer"):
                self.tailer.offset = 0
            self.update_status(f"Pruned log >4 MB to {result.archive_path.name if result.archive_path else 'archive'}")

    def pick_log_file(self) -> None:
        initial_dir = self.settings.last_log_dir
        path = filedialog.askopenfilename(
            title="Select Project1999 log file",
            initialdir=str(initial_dir if initial_dir.exists() else Path.home()),
            filetypes=[("EQ log files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.open_log_path(Path(path), scan=True, silent=False)

    def open_latest_active_log(self) -> None:
        log_path = latest_active_log(self.settings.last_log_dir)
        if not log_path:
            messagebox.showwarning("EQGPS", f"No eqlog_*.txt files found in:\n{self.settings.last_log_dir}")
            self.update_status("No recent P99 logs found")
            return
        self.open_log_path(log_path, scan=True, silent=False)
        self.update_status(f"Auto-opened latest log: {log_path.name}")

    def open_log_path(self, path: Path, scan: bool, silent: bool) -> None:
        if not path.exists():
            if not silent:
                messagebox.showwarning("EQGPS", f"Log file does not exist:\n{path}")
            self.update_status(f"Log missing: {path}")
            return
        self.settings.log_path = path
        if hasattr(self, "tailer"):
            self.tailer.set_path(path)
        pruned_archive_name: str | None = None
        log_open_status: str | None = None
        if scan:
            self.current_zone_name = None
            self.current_zone_key = None
            self.current_loc = None
            self.cursor_world = None
            self.layer_states = []
            self.raw_map_bounds = None
            self.map_bounds = None
            self.current_calibration = ZoneCalibration()
            self.heading = HeadingTracker(min_distance=3.0)
            self._batching_log_scan = True
            outcome = read_then_prune_safely(
                self.tailer.scan_existing,
                lambda: maybe_prune_log(path),
            )
            self._batching_log_scan = False
            log_open_status = outcome.status_text("scan")
            if log_open_status:
                self.update_status(log_open_status)
            elif outcome.prune_result and outcome.prune_result.pruned:
                self.tailer.offset = 0
                pruned_archive_name = outcome.prune_result.archive_path.name if outcome.prune_result.archive_path else "archive"
        else:
            self.prune_log_if_needed(path)
        if pruned_archive_name:
            self.update_status(f"Watching log; pruned >4 MB to {pruned_archive_name}")
        elif log_open_status:
            self.update_status(log_open_status)
        else:
            self.update_status("Watching log")
        self.render()

    def should_render_immediately(self) -> bool:
        return not self._batching_log_scan

    def reload_map_keys(self) -> None:
        ensure_map_files_available(self.map_dir)
        self.map_keys = MapKeys.load(self.map_dir / "map_keys.ini", self.map_dir / "map_keys_who.ini")
        if self.current_zone_name:
            self.handle_zone(self.current_zone_name)
        self.update_status("Reloaded map key files")

    def poll_log(self) -> None:
        outcome = read_then_prune_safely(
            self.tailer.poll_new_lines,
            lambda: maybe_prune_log(self.settings.log_path),
        )
        status_text = outcome.status_text("poll")
        if status_text:
            self.update_status(status_text)
        elif outcome.prune_result and outcome.prune_result.pruned:
            self.tailer.offset = 0
            archive_name = outcome.prune_result.archive_path.name if outcome.prune_result.archive_path else "archive"
            self.update_status(f"Watching log; pruned >4 MB to {archive_name}")
        else:
            if is_log_stale(self.settings.log_path, stale_after_seconds=DEFAULT_STALE_SECONDS):
                self.update_status("Log appears stale; no new lines for 5+ minutes")
            else:
                self.update_status("Watching log")
        active_markers = self.marker_store.for_zone(self.current_zone_key)
        if any(marker.timer_started_at for marker in active_markers):
            self.notify_ready_timers(active_markers)
            self.rebuild_marker_panel()
            self.render()
        self.after(750, self.poll_log)

    def handle_zone(self, zone_name: str) -> None:
        zone_key = self.map_keys.resolve(zone_name)
        previous_loc = self.current_loc
        self.state.update_zone(zone_name, zone_key)
        self.current_zone_name = self.state.current_zone_name
        self.current_zone_key = self.state.current_zone_key
        self.current_loc = self.state.current_loc
        if previous_loc is not None and self.current_loc is None:
            self.heading = HeadingTracker(min_distance=3.0)
        self.layer_states = []
        self.raw_map_bounds = None
        self.map_bounds = None
        self.current_calibration = ZoneCalibration.from_dict(self.settings.get_zone_calibration(self.current_zone_key))
        if self.current_zone_key:
            layers = discover_zone_layers(self.map_dir, self.current_zone_key)
            for layer in layers:
                prefs = self.settings.get_layer_settings(self.current_zone_key, layer.name)
                visible_var = tk.BooleanVar(value=bool(prefs.get("visible", True)))
                opacity_var = tk.IntVar(value=int(prefs.get("opacity", 100)))
                self.layer_states.append(LayerState(layer, parse_map_file(layer.path), visible_var, opacity_var))
            self.raw_map_bounds = self.combined_bounds([state.parsed for state in self.layer_states])
            self.map_bounds = apply_calibration_to_bounds(self.raw_map_bounds, self.current_calibration)
            self.rebuild_layer_panel()
            self.rebuild_marker_panel()
            self.request_fit_map()
        else:
            self.rebuild_layer_panel()
            self.rebuild_marker_panel()
        self.update_status("Zone changed")
        if self.should_render_immediately():
            self.render()

    def handle_loc(self, loc: Loc) -> None:
        self.state.update_loc(loc)
        self.current_loc = self.state.current_loc
        self.heading.add_sample(loc)
        self.update_status("Location updated")
        if self.should_render_immediately():
            self.render()

    def handle_sense_heading(self, heading_text: str) -> None:
        self.heading.set_sense_heading(heading_text)
        self.update_status(f"Sense heading: {heading_text}")
        if self.should_render_immediately():
            self.render()

    @staticmethod
    def combined_bounds(layers: list[ParsedMap]) -> tuple[float, float, float, float] | None:
        bounds = [layer.bounds for layer in layers if layer.bounds]
        if not bounds:
            return None
        min_x = min(b[0] for b in bounds)
        min_y = min(b[1] for b in bounds)
        max_x = max(b[2] for b in bounds)
        max_y = max(b[3] for b in bounds)
        return min_x, min_y, max_x, max_y

    def viewport(self) -> ViewportTransform | None:
        if not self.map_bounds:
            return None
        return ViewportTransform(self.map_bounds, self.scale, self.offset_x, self.offset_y)

    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        viewport = self.viewport()
        if not viewport:
            return x, y
        return viewport.world_to_screen(x, y)

    def screen_to_world(self, x: float, y: float) -> tuple[float, float] | None:
        viewport = self.viewport()
        if not viewport:
            return None
        return viewport.screen_to_world(x, y)

    def rebuild_layer_panel(self) -> None:
        for child in self.layer_frame.winfo_children():
            child.destroy()
        if not self.layer_states:
            ttk.Label(self.layer_frame, text="No layers loaded").pack(anchor=tk.W, padx=4, pady=4)
            return
        for state in self.layer_states:
            row = ttk.Frame(self.layer_frame)
            row.pack(fill=tk.X, pady=compact_layer_row_padding(3))
            check = ttk.Checkbutton(
                row,
                text=state.layer.name,
                variable=state.visible_var,
                command=lambda s=state: self.on_layer_changed(s),
            )
            check.pack(side=tk.LEFT, anchor=tk.W)
            scale = ttk.Scale(
                row,
                from_=0,
                to=100,
                orient=tk.HORIZONTAL,
                variable=state.opacity_var,
                length=compact_slider_length(120),
                command=lambda _value, s=state: self.on_layer_changed(s),
            )
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 2))
            ttk.Label(row, textvariable=state.opacity_var, width=3).pack(side=tk.RIGHT)

    def rebuild_marker_panel(self) -> None:
        if not self.marker_list:
            return
        selected = self.selected_marker_id()
        self.marker_list.delete(0, tk.END)
        self.marker_list_ids = []
        query = self.marker_search_var.get() if self.marker_search_var else ""
        for marker in self.marker_store.search(self.current_zone_key, query=query):
            timer = marker_timer_state(marker)
            text = f"{marker.label} ({marker.category})"
            if timer:
                text = f"{text} [{timer}]"
            self.marker_list.insert(tk.END, text)
            self.marker_list_ids.append(marker.id)
            if marker.id == selected:
                self.marker_list.selection_set(tk.END)

    def selected_marker_id(self) -> str | None:
        if not self.marker_list:
            return None
        selection = self.marker_list.curselection()
        if not selection:
            return None
        index = int(selection[0])
        if index < 0 or index >= len(self.marker_list_ids):
            return None
        return self.marker_list_ids[index]

    def select_marker_from_list(self) -> None:
        marker = self.marker_store.get(self.selected_marker_id() or "")
        if marker:
            self.cursor_world = (marker.x, marker.y)
            self.update_status("Marker selected")
            self.render()

    def set_selected_marker_waypoint(self) -> None:
        marker_id = self.selected_marker_id()
        if not marker_id:
            return
        self.marker_store.set_waypoint(marker_id)
        self.save_markers()
        self.update_status("Waypoint set")
        self.render()

    def edit_marker_details(self, marker: Marker) -> bool:
        label = simpledialog.askstring("EQGPS Marker", "Marker label:", initialvalue=marker.label, parent=self)
        if label is None:
            return False
        category = simpledialog.askstring("EQGPS Marker", "Category:", initialvalue=marker.category, parent=self)
        if category is None:
            return False
        notes = simpledialog.askstring("EQGPS Marker", "Notes:", initialvalue=marker.notes, parent=self)
        if notes is None:
            return False
        update_marker_details(marker, label=label, category=category, notes=notes)
        self.save_markers()
        self.update_status("Marker updated")
        self.render()
        return True

    def edit_selected_marker(self) -> None:
        marker = self.marker_store.get(self.selected_marker_id() or "")
        if marker:
            self.edit_marker_details(marker)

    def current_marker_timer_seconds(self) -> int:
        if not self.marker_timer_text_var:
            return DEFAULT_TIMER_SECONDS
        try:
            seconds = normalize_timer_seconds(self.marker_timer_text_var.get())
        except tk.TclError:
            seconds = DEFAULT_TIMER_SECONDS
        self.marker_timer_text_var.set(format_timer_duration(seconds))
        self.settings.set_marker_timer_seconds(seconds)
        return seconds

    def start_selected_marker_timer(self) -> None:
        marker = self.marker_store.get(self.selected_marker_id() or "")
        if not marker:
            return
        seconds = self.current_marker_timer_seconds()
        reset_marker_timer(marker, seconds=seconds)
        self.save_markers()
        self.update_status(f"{format_timer_duration(seconds)} timer started")
        self.render()

    def reset_selected_marker_timer(self) -> None:
        marker = self.marker_store.get(self.selected_marker_id() or "")
        if not marker:
            return
        seconds = self.current_marker_timer_seconds()
        reset_marker_timer_paused(marker, seconds=seconds)
        self.save_markers()
        self.update_status(f"{format_timer_duration(seconds)} timer reset (paused)")
        self.render()

    def clear_selected_marker_timer(self) -> None:
        marker = self.marker_store.get(self.selected_marker_id() or "")
        if not marker:
            return
        clear_marker_timer(marker)
        self.save_markers()
        self.update_status("Timer cleared")
        self.render()

    def delete_selected_marker(self) -> None:
        marker_id = self.selected_marker_id()
        if not marker_id:
            return
        self.marker_store.remove(marker_id)
        self.save_markers()
        self.update_status("Marker deleted")
        self.render()

    def export_markers(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export EQGPS markers",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(self.marker_store.to_dict(), indent=2), encoding="utf-8")
        self.update_status("Markers exported")

    def import_markers(self) -> None:
        path = filedialog.askopenfilename(
            title="Import EQGPS markers",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.marker_store.merge_import(MarkerStore.from_dict(data))
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            messagebox.showwarning("EQGPS", f"Could not import markers:\n{exc}")
            return
        self.save_markers()
        self.update_status("Markers imported")
        self.render()

    def save_timer_sound_settings(self) -> None:
        enabled = bool(self.timer_sound_enabled_var.get()) if self.timer_sound_enabled_var else True
        path = self.timer_sound_path_var.get() if self.timer_sound_path_var else self.initial_timer_sound_path
        self.settings.set_timer_sound_settings(enabled, path)

    def pick_timer_sound(self) -> None:
        current = Path(self.timer_sound_path_var.get()) if self.timer_sound_path_var else Path(default_windows_sound_path())
        path = filedialog.askopenfilename(
            title="Select timer notification sound",
            initialdir=str(current.parent if current.parent.exists() else Path(default_windows_sound_path()).parent),
            filetypes=[("Wave sounds", "*.wav"), ("All files", "*.*")],
        )
        if not path:
            return
        if self.timer_sound_path_var:
            self.timer_sound_path_var.set(path)
        self.save_timer_sound_settings()
        self.update_status("Timer sound selected")

    def play_timer_sound(self) -> None:
        if self.timer_sound_enabled_var and not self.timer_sound_enabled_var.get():
            return
        path = self.timer_sound_path_var.get() if self.timer_sound_path_var else self.initial_timer_sound_path
        try:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            try:
                self.bell()
            except tk.TclError:
                pass

    def test_timer_sound(self) -> None:
        self.save_timer_sound_settings()
        self.play_timer_sound()
        self.update_status("Timer sound tested")

    def notify_ready_timers(self, markers: list[Marker]) -> None:
        ready_ids = self.timer_sound_notifier.ready_marker_ids(markers, now=time.time())
        if not ready_ids:
            return
        self.play_timer_sound()
        ready_names = [self.marker_store.get(marker_id).label for marker_id in ready_ids if self.marker_store.get(marker_id)]
        self.update_status(f"Timer ready: {', '.join(ready_names) if ready_names else len(ready_ids)}")

    def on_layer_changed(self, state: LayerState) -> None:
        if self.current_zone_key:
            self.settings.set_layer_settings(
                self.current_zone_key,
                state.layer.name,
                state.visible_var.get(),
                int(state.opacity_var.get()),
            )
        self.render()

    def current_elevation_filter(self) -> ElevationFilter:
        if not self.elevation_enabled_var or not self.elevation_above_var or not self.elevation_below_var:
            return self.initial_elevation_filter

        def safe_distance(var: tk.DoubleVar, fallback: float) -> float:
            try:
                return max(0.0, float(var.get()))
            except (tk.TclError, ValueError):
                return fallback

        return ElevationFilter(
            enabled=bool(self.elevation_enabled_var.get()),
            above=safe_distance(self.elevation_above_var, self.initial_elevation_filter.above),
            below=safe_distance(self.elevation_below_var, self.initial_elevation_filter.below),
        )

    def on_elevation_changed(self) -> None:
        elevation = self.current_elevation_filter()
        self.settings.set_elevation_filter(elevation.enabled, elevation.above, elevation.below)
        self.update_status("Elevation filter updated")
        self.render()

    def request_fit_map(self) -> None:
        self.pending_fit_map = True
        self.after_idle(self.fit_map)

    def on_canvas_configure(self, _event: tk.Event) -> None:
        if self.pending_fit_map:
            self.fit_map()
        else:
            self.render()

    def fit_map(self) -> None:
        if not self.map_bounds:
            self.pending_fit_map = False
            self.render()
            return
        fit = fit_viewport_to_bounds(self.map_bounds, self.canvas.winfo_width(), self.canvas.winfo_height())
        if fit is None:
            self.pending_fit_map = True
            self.render()
            return
        self.scale, self.offset_x, self.offset_y = fit
        self.pending_fit_map = False
        self.render()

    def center_player(self) -> None:
        if not self.current_loc or not self.map_bounds:
            return
        player = loc_to_map_point(self.current_loc)
        px, py = self.world_to_screen(player.x, player.y)
        self.offset_x += self.canvas.winfo_width() / 2 - px
        self.offset_y += self.canvas.winfo_height() / 2 - py
        self.clamp_pan()
        self.render()

    def on_mousewheel_delta(self, event: tk.Event, delta: int) -> None:
        self.zoom_at(event.x, event.y, delta)

    def on_mousewheel(self, event: tk.Event) -> None:
        self.zoom_at(event.x, event.y, event.delta)

    def zoom_at(self, x: int, y: int, delta: int) -> None:
        factor = 1.12 if delta > 0 else 1 / 1.12
        old_scale = self.scale
        self.scale = max(0.02, min(self.scale * factor, 30.0))
        if old_scale:
            self.offset_x = x - (x - self.offset_x) * (self.scale / old_scale)
            self.offset_y = y - (y - self.offset_y) * (self.scale / old_scale)
        self.clamp_pan()
        self.cursor_world = self.screen_to_world(x, y)
        self.update_status("Watching log")
        self.render()

    def on_drag_start(self, event: tk.Event) -> None:
        self.drag_start = (event.x, event.y)

    def on_drag(self, event: tk.Event) -> None:
        if not self.drag_start:
            return
        last_x, last_y = self.drag_start
        self.offset_x += event.x - last_x
        self.offset_y += event.y - last_y
        self.drag_start = (event.x, event.y)
        self.clamp_pan()
        self.on_mouse_move(event)
        self.render()

    def on_drag_end(self, _event: tk.Event) -> None:
        self.drag_start = None

    def on_mouse_move(self, event: tk.Event) -> None:
        self.cursor_world = self.screen_to_world(event.x, event.y)
        self.update_status("Watching log")

    def on_mouse_leave(self, _event: tk.Event) -> None:
        self.cursor_world = None
        self.update_status("Watching log")

    def on_context_menu(self, event: tk.Event) -> None:
        self.context_world = self.screen_to_world(event.x, event.y)
        self.context_marker_id = self.find_marker_near_screen(event.x, event.y)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Add Marker Here", command=self.add_marker_here)
        if self.context_marker_id:
            menu.add_separator()
            menu.add_command(label="Set as Waypoint", command=self.set_context_marker_waypoint)
            menu.add_command(label="Edit Marker", command=self.edit_context_marker)
            menu.add_command(label="Start Timer...", command=self.start_context_marker_timer)
            menu.add_command(label="Reset Timer", command=self.reset_context_marker_timer)
            menu.add_command(label="Clear Timer", command=self.clear_context_marker_timer)
            menu.add_command(label="Delete Marker", command=self.delete_context_marker)
        if self.marker_store.active_waypoint_id:
            menu.add_separator()
            menu.add_command(label="Clear Waypoint", command=self.clear_waypoint)
        menu.tk_popup(event.x_root, event.y_root)

    def find_marker_near_screen(self, screen_x: int, screen_y: int, radius: float = 14.0) -> str | None:
        closest_id = None
        closest_distance = radius
        for marker in self.marker_store.for_zone(self.current_zone_key):
            mx, my = self.world_to_screen(marker.x, marker.y)
            distance = math.hypot(screen_x - mx, screen_y - my)
            if distance <= closest_distance:
                closest_distance = distance
                closest_id = marker.id
        return closest_id

    def save_markers(self) -> None:
        self.settings.set_marker_data(self.marker_store.to_dict())
        self.rebuild_marker_panel()

    def add_marker_here(self) -> None:
        if not self.current_zone_key or not self.context_world:
            return
        label = simpledialog.askstring("EQGPS Marker", "Marker label:", parent=self)
        if not label:
            return
        category = simpledialog.askstring("EQGPS Marker", "Category:", initialvalue="Custom", parent=self) or "Custom"
        timer_text = simpledialog.askstring(
            "EQGPS Marker",
            "Timer mm:ss (blank for none):",
            initialvalue=format_timer_duration(self.current_marker_timer_seconds()),
            parent=self,
        )
        timer_seconds = None
        timer_minutes = None
        timer_started_at = None
        if timer_text and timer_text.strip():
            timer_seconds = normalize_timer_seconds(timer_text)
            timer_minutes = max(1, math.ceil(timer_seconds / 60))
            timer_started_at = time.time()
        marker = Marker(
            zone_key=self.current_zone_key,
            x=self.context_world[0],
            y=self.context_world[1],
            label=label.strip(),
            category=category.strip() or "Custom",
            timer_minutes=timer_minutes,
            timer_seconds=timer_seconds,
            timer_started_at=timer_started_at,
        )
        self.marker_store.add(marker)
        self.save_markers()
        self.update_status("Marker added")
        self.render()

    def set_context_marker_waypoint(self) -> None:
        self.marker_store.set_waypoint(self.context_marker_id)
        self.save_markers()
        self.update_status("Waypoint set")
        self.render()

    def edit_context_marker(self) -> None:
        marker = self.marker_store.get(self.context_marker_id or "")
        if marker:
            self.edit_marker_details(marker)

    def clear_waypoint(self) -> None:
        self.marker_store.set_waypoint(None)
        self.save_markers()
        self.update_status("Waypoint cleared")
        self.render()

    def start_context_marker_timer(self) -> None:
        marker = self.marker_store.get(self.context_marker_id or "")
        if not marker:
            return
        timer_text = simpledialog.askstring(
            "EQGPS Timer",
            "Timer mm:ss:",
            initialvalue=format_timer_duration(self.current_marker_timer_seconds()),
            parent=self,
        )
        if timer_text is None:
            return
        seconds = normalize_timer_seconds(timer_text)
        if self.marker_timer_text_var:
            self.marker_timer_text_var.set(format_timer_duration(seconds))
        self.settings.set_marker_timer_seconds(seconds)
        reset_marker_timer(marker, seconds=seconds)
        self.save_markers()
        self.update_status(f"{format_timer_duration(seconds)} timer started")
        self.render()

    def reset_context_marker_timer(self) -> None:
        marker = self.marker_store.get(self.context_marker_id or "")
        if not marker:
            return
        seconds = self.current_marker_timer_seconds()
        reset_marker_timer_paused(marker, seconds=seconds)
        self.save_markers()
        self.update_status(f"{format_timer_duration(seconds)} timer reset (paused)")
        self.render()

    def clear_context_marker_timer(self) -> None:
        marker = self.marker_store.get(self.context_marker_id or "")
        if not marker:
            return
        clear_marker_timer(marker)
        self.save_markers()
        self.update_status("Timer cleared")
        self.render()

    def delete_context_marker(self) -> None:
        if not self.context_marker_id:
            return
        self.marker_store.remove(self.context_marker_id)
        self.save_markers()
        self.update_status("Marker deleted")
        self.render()

    def refresh_calibrated_bounds(self) -> None:
        self.map_bounds = apply_calibration_to_bounds(self.raw_map_bounds, self.current_calibration)

    def save_zone_calibration(self) -> None:
        if self.current_zone_key:
            self.settings.set_zone_calibration(self.current_zone_key, self.current_calibration.to_dict())

    def nudge_zone_calibration(self, dx: float, dy: float) -> None:
        if not self.current_zone_key or not self.raw_map_bounds:
            return
        self.current_calibration = self.current_calibration.nudged(dx, dy)
        self.refresh_calibrated_bounds()
        self.save_zone_calibration()
        self.request_fit_map()
        self.update_status(f"Calibration: {self.current_calibration.offset_x:.0f}, {self.current_calibration.offset_y:.0f}")

    def reset_zone_calibration(self) -> None:
        if not self.current_zone_key:
            return
        self.current_calibration = ZoneCalibration()
        self.refresh_calibrated_bounds()
        self.save_zone_calibration()
        self.request_fit_map()
        self.update_status("Calibration reset")

    def clamp_pan(self) -> None:
        self.offset_x, self.offset_y = clamp_pan_units(self.offset_x, self.offset_y, self.scale, max_units=10000.0)

    def render(self) -> None:
        self.canvas.delete("all")
        self.canvas.configure(bg=self.current_chrome_background())
        self.draw_canvas_chrome_background()
        if not self.layer_states:
            msg = "No map loaded yet"
            if self.current_zone_name and not self.current_zone_key:
                msg = f"Zone '{self.current_zone_name}' not found in map_keys.ini or map_keys_who.ini"
            elif self.current_zone_key:
                msg = f"No map .txt layers found for key '{self.current_zone_key}'"
            self.canvas.create_text(20, 20, text=msg, fill=FG, anchor=tk.NW, font=("Segoe UI", 12))
            return

        map_dx = self.current_calibration.offset_x
        map_dy = self.current_calibration.offset_y
        elevation = self.current_elevation_filter()
        player_z = self.current_loc.z if self.current_loc else None
        for state in self.layer_states:
            if not state.visible_var.get():
                continue
            opacity = int(state.opacity_var.get())
            for line in state.parsed.lines:
                if not line_visible_at_player_z(line, player_z, elevation):
                    continue
                x1, y1 = self.world_to_screen(line.x1 + map_dx, line.y1 + map_dy)
                x2, y2 = self.world_to_screen(line.x2 + map_dx, line.y2 + map_dy)
                self.canvas.create_line(x1, y1, x2, y2, fill=rgb_to_hex(blend_with_bg(line.color, opacity)), width=1)
            for label in state.parsed.labels:
                if not label_visible_at_player_z(label, player_z, elevation):
                    continue
                x, y = self.world_to_screen(label.x + map_dx, label.y + map_dy)
                self.canvas.create_text(x, y, text=label.text, fill=rgb_to_hex(blend_with_bg(label.color, opacity)), anchor=tk.CENTER, font=("Segoe UI", 8))

        self.render_markers()
        self.render_player_marker()

    def render_markers(self) -> None:
        for marker in self.marker_store.for_zone(self.current_zone_key):
            x, y = self.world_to_screen(marker.x, marker.y)
            fill = marker.color
            timer_state = marker_timer_state(marker)
            label = marker.label
            if timer_state:
                label = f"{label} [{timer_state}]"
                if timer_state == "READY":
                    fill = "#ff4444"
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=fill, outline="#111111", width=1)
            self.canvas.create_text(x + 8, y - 8, text=label, fill=fill, anchor=tk.SW, font=("Segoe UI", 8, "bold"))

        waypoint = self.marker_store.active_waypoint()
        if waypoint and waypoint.zone_key == self.current_zone_key:
            wx, wy = self.world_to_screen(waypoint.x, waypoint.y)
            self.canvas.create_oval(wx - 10, wy - 10, wx + 10, wy + 10, outline=WAYPOINT_COLOR, width=2)
            self.canvas.create_text(wx + 12, wy + 10, text="WAYPOINT", fill=WAYPOINT_COLOR, anchor=tk.NW, font=("Segoe UI", 8, "bold"))
            if self.current_loc:
                player = loc_to_map_point(self.current_loc)
                px, py = self.world_to_screen(player.x, player.y)
                self.canvas.create_line(px, py, wx, wy, fill=WAYPOINT_COLOR, dash=(4, 4), width=1)

    def render_player_marker(self) -> None:
        if not self.current_loc:
            return
        player = loc_to_map_point(self.current_loc)
        x, y = self.world_to_screen(player.x, player.y)
        heading = self.heading.heading_degrees
        if heading is None:
            size = 8
            self.canvas.create_oval(x - size, y - size, x + size, y + size, outline=PLAYER_COLOR, width=2)
            self.canvas.create_line(x, y - 18, x, y + 18, fill=PLAYER_COLOR, width=2)
            self.canvas.create_line(x - 18, y, x + 18, y, fill=PLAYER_COLOR, width=2)
        else:
            # EQ/world y increases upward in this renderer, so screen-space y is inverted.
            radians = math.radians(heading)
            tip = (x + math.cos(radians) * 22, y - math.sin(radians) * 22)
            left = (x + math.cos(radians + 2.45) * 14, y - math.sin(radians + 2.45) * 14)
            right = (x + math.cos(radians - 2.45) * 14, y - math.sin(radians - 2.45) * 14)
            self.canvas.create_polygon(tip, left, right, fill="", outline=PLAYER_COLOR, width=2)
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill=PLAYER_COLOR, outline=PLAYER_COLOR)
        self.canvas.create_text(x + 12, y - 12, text="You", fill=PLAYER_COLOR, anchor=tk.SW, font=("Segoe UI", 9, "bold"))

    def render_overlay(self) -> None:
        lines = []
        if self.current_loc:
            lines.append(f"Player: {self.current_loc.x:.1f}, {self.current_loc.y:.1f}, {self.current_loc.z:.1f}")
            if self.heading.heading_degrees is not None:
                lines.append(f"Heading: {self.heading.heading_degrees:.1f}°")
        if self.cursor_world:
            cursor_loc_x, cursor_loc_y = map_point_to_loc_xy(self.cursor_world)
            lines.append(f"Cursor: {cursor_loc_x:.1f}, {cursor_loc_y:.1f}")
            if self.current_loc:
                player = loc_to_map_point(self.current_loc)
                distance = math.hypot(self.cursor_world[0] - player.x, self.cursor_world[1] - player.y)
                lines.append(f"Dist: {distance:.1f}")
        if not lines:
            return
        text = "\n".join(lines)
        self.canvas.create_rectangle(10, 10, 260, 28 + len(lines) * 18, fill="#000000", outline="#333333")
        self.canvas.create_text(18, 18, text=text, fill=FG, anchor=tk.NW, font=("Consolas", 10))

    def update_status(self, prefix: str) -> None:
        waypoint = self.marker_store.active_waypoint()
        if waypoint and waypoint.zone_key != self.current_zone_key:
            waypoint = None
        snapshot = StatusSnapshot(
            prefix=prefix,
            zone_name=self.current_zone_name,
            zone_key=self.current_zone_key,
            current_loc=self.current_loc,
            cursor_world=self.cursor_world,
            layer_count=len(self.layer_states),
            waypoint=waypoint,
            elevation=self.current_elevation_filter(),
            calibration=self.current_calibration,
            log_path=str(self.settings.log_path),
        )
        self.status_var.set(snapshot.status_text)
        self.bottom_var.set(format_bottom_status(snapshot))

    def on_close(self) -> None:
        self.set_window_click_through(False)
        self.settings.remember_window_geometry(self.geometry())
        if self.overlay_tray and self.overlay_tray.winfo_exists():
            self.overlay_tray.destroy()
        self.destroy()


def main() -> None:
    app = EQGPSApp()
    app.mainloop()


if __name__ == "__main__":
    main()
