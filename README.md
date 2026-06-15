# EQGPS

EQGPS is a passive Project1999/EverQuest map companion for Windows. It reads your local EverQuest log file, watches for zone and `/loc` output, and shows your position on bundled EQ map files.

EQGPS does **not** automate gameplay, inject into the client, or send keypresses. It only reads log text that EverQuest has already written to disk.

## Current features

- Opens/remembers a selected P99 log file.
- Can auto-open the newest `eqlog_*.txt` file from the last log directory.
- Warns in the status tray when the selected log file appears stale for 5+ minutes.
- Automatically prunes selected logs over 4 MB by archiving old contents to an ISO date-time suffix, then truncating the active log.
- Tails the log file for new lines.
- Parses zone loads from `You have entered ...`.
- Infers zone from `/who` output by extracting the character name from the log filename, matching that character's `[level class] Name (race)` row, then reading the next `There are N players in Zone.` line.
- Parses `/loc` output from `Your Location is x, y, z`.
- Resolves zone names through `map_files/map_keys.ini` plus aliases from `map_files/map_keys_who.ini`.
- Loads matching bundled map `.txt` layers for the current zone.
- Renders maps on a dark background with black map lines brightened for visibility.
- Supports pan with left-drag, zoom with mouse wheel, fit map, and center-player.
- Shows a right-side layer panel with per-layer show/hide checkboxes and opacity sliders.
- Remembers layer preferences by zone.
- Caps pan to 10,000 map units from center.
- Shows player location, cursor map location, and distance from player to cursor.
- Converts P99 `/loc` output as `player_map_x = -loc_y`, `player_map_y = loc_x`; raw EQ map geometry is drawn as `map_x = raw_x`, `map_y = -raw_y`.
- Parses Sense Heading lines like `You think you are heading East.` and estimates heading from repeated `/loc` samples.
- Right-click map to add persistent custom markers.
- Right-click existing markers to set waypoint, edit label/category/notes, start/reset/clear timers, or delete.
- Shows current-zone markers in the side panel with text search.
- Supports marker JSON import/export for backup or sharing.
- Provides an elevation filter for 3D maps: hide/show map lines and labels by Z distance above/below the most recent `/loc` Z value.
- Draws waypoint ring/line from player and shows waypoint distance in the bottom bar.
- Timer notifications can play a selected `.wav` file.
- Provides per-zone map calibration: Ctrl+Arrow nudges 10 units, Ctrl+Shift+Arrow nudges 100 units, and Reset Cal clears the zone offset.
- Adds a right-sidebar peekaboo arrow (`>`/`<`) that hides or reopens the side panel.
- Adds persistent Always on Top, Mini Mode, Transparent UI, and Borderless Overlay modes.
- Borderless Overlay mode includes Restore Normal, opacity, click-through, lock-window, Always on Top, and Mini Mode controls.
- Keyboard shortcuts: `F` fit map, `C` center player, `W` clear waypoint, and `T` toggle the side tray.
- Remembers window size/position on close.

## Requirements

- Windows 10/11.
- Python 3.11+ recommended.
- Tkinter, which is included with the standard Python.org Windows installer.
- Project1999/EverQuest logging enabled.

No third-party Python packages are required for normal use.

## Quick start

1. Download or clone this repository.
2. Make sure EverQuest logging is enabled in game:

   ```text
   /log on
   ```

3. Run EQGPS by double-clicking:

   ```text
   launch_eqgps.pyw
   ```

   Or from a terminal:

   ```bash
   python launch_eqgps.pyw
   ```

4. Click **Open Log File** and choose your active P99 log, usually under a folder like:

   ```text
   C:\Users\Public\EQ_P99\Logs\eqlog_Yourcharacter_P1999Green.txt
   ```

5. In game, use `/loc`, zone, or run `/who` so EQGPS can update your zone and location.

The bundled maps live in `map_files/`. By default EQGPS looks for this folder next to the application files, so a normal clone/download should work without editing paths.

## Runtime data

EQGPS stores your selected log path, window settings, layer preferences, markers, timers, and calibration data in your Windows roaming AppData folder:

```text
%APPDATA%\EQGPS\settings.json
```

Runtime data is intentionally not stored in the repository.

## Running tests

The test suite uses the Python standard library `unittest` runner:

```bash
python -m unittest discover -s tests -q
```

## Bucket list / not implemented yet

### UI and layout

- Add extra keyboard shortcuts for future actions such as add marker and toggle follow-player once those workflows exist.

### Log and character quality-of-life

- Add a recent-log dropdown and character/profile selector.
- Support multiple character profiles/settings.

### Markers and spawn tools

- Replace free-text marker categories with a dedicated category dropdown.
- Add category-based default colors/icons.
- Add category-specific default timer lengths.
- Add timer pause/resume and overdue state beyond READY.
- Add a timer dashboard/list for all active spawn timers in the current zone.

### Navigation and tracking

- Add an edge-of-screen waypoint arrow when the waypoint is off-screen.
- Add bearing/direction text to waypoint.
- Add a temporary target point separate from persistent markers.
- Add movement trail/breadcrumb path from repeated `/loc` output, with clear trail/session recording options.
- Add distance rings and a measuring tool between arbitrary points.

### Map calibration and diagnostics

- Add per-zone scale and rotation calibration, beyond the current X/Y offset nudges.
- Add a calibration wizard using known `/loc` anchor points.
- Add map/key diagnostics showing zones without maps and maps without key entries.
- Add a UI editor for `map_keys.ini` and `map_keys_who.ini` aliases.
- Add map layer reorder controls, layer display-name editing, and optional per-layer color overrides.

### Elevation filter polish

- Add per-zone elevation defaults.
- Add per-layer elevation filter overrides.
- Add quick elevation presets such as current floor only, nearby floors, and show all.
- Add a fade-out option for out-of-range elevation geometry instead of only hiding it.

### Packaging and release polish

- Build a standalone `.exe`.
- Add an installer or desktop shortcut creator.
- Add settings backup/restore.
- Add an error/crash log viewer.
