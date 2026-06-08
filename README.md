# EQGPS

EQGPS is a passive Project1999/EverQuest map companion.

Phase 1-18 features implemented:

- Opens/remembers a selected P99 log file.
- Can auto-open the newest `eqlog_*.txt` file from the last log directory.
- Warns in the status tray when the selected log file appears stale for 5+ minutes.
- Automatically prunes selected logs over 4 MB by archiving the old contents to a filename with an ISO date-time suffix, then truncating the active log.
- Tails the log file for new lines.
- Parses zone loads from `You have entered ...`.
- Infers zone from `/who` output by extracting the character name from the log filename, matching the character's `[level class] Name (race)` row, then reading the next `There are N players in Zone.` line.
- Parses `/loc` output from `Your Location is x, y, z`.
- Resolves zone names through `map_files/map_keys.ini` plus aliases from `map_files/map_keys_who.ini`.
- Loads matching map `.txt` layers for the current zone.
- Renders the map on a dark background with black map lines brightened for visibility.
- Shows current zone, resolved map key, current `/loc`, layer count, log path, and map path.
- Supports pan with left-drag, zoom with mouse wheel, fit map, and center-player.
- Automatically refits the map after each zone change once the canvas has a real window size, avoiding startup/zone-load min-zoom fits.
- Shows a right-side layer panel with per-layer show/hide checkboxes.
- Shows per-layer opacity sliders and remembers layer preferences by zone.
- Compacts each layer row into a single-line checkbox/opacity slider layout to fit roughly twice as many layers vertically.
- Caps pan to 10,000 map units from center.
- Shows player location, cursor map location, and distance from player to cursor.
- Converts EQ `/loc` output to player/heading coordinates as `player_map_x = -loc_y`, `player_map_y = loc_x`, fixing Oasis east/west movement; draws raw EQ map `.txt` geometry as `map_x = raw_x`, `map_y = -raw_y`, fixing East Commonlands top/bottom flip.
- Parses Sense Heading lines like `You think you are heading East.` and uses them to update the heading marker.
- Estimates heading from repeated `/loc` samples and draws a directional player marker.
- Right-click map to add persistent custom markers.
- Right-click existing markers to set waypoint, edit label/category/notes, start/reset/clear an adjustable 1-minute-step timer, or delete.
- Shows current-zone markers in the side panel with text search.
- Side-panel marker actions can set waypoint, edit label/category/notes, start/reset/clear a custom minute timer, or delete the selected marker.
- Supports marker JSON import/export for backup or sharing.
- Provides an elevation filter for 3D maps: hide/show map lines and labels by Z distance above/below the most recent `/loc` Z value.
- Elevation filter settings are controlled from the side panel and remembered between launches.
- Draws waypoint ring/line from player and shows waypoint distance in the bottom bar.
- Marker timers count down and display READY when expired.
- Timer notifications can play a selected `.wav` file; the default picker path uses the Windows Sounds folder.
- Provides per-zone map calibration: Ctrl+Arrow nudges the map 10 units, Ctrl+Shift+Arrow nudges 100 units, and Reset Cal clears the zone offset.
- Shows the current per-zone calibration offset in the bottom bar.
- Moves detailed zone/player/cursor/layer info to the bottom bar instead of covering the map.
- Uses a narrower map-layer side panel.
- Adds a right-sidebar peekaboo arrow (`>`/`<`) that hides or reopens the side panel for more map space.
- Moves the former top toolbar buttons into a Controls section at the top of the slide-out side tray.
- Adds vertical scrolling to the slide-out side tray so all controls remain reachable as the tray grows.
- Adds a persistent Always on Top checkbox in the Controls tray.
- Adds a persistent Mini Mode checkbox that shrinks the window and hides the side/bottom chrome for a compact map view.
- Adds a persistent Transparent UI checkbox plus Window/UI slider from fully transparent to normal.
- Adds Borderless Overlay mode for transparency without fading the drawn map: the native border/titlebar is removed, the map stays opaque, and a separate Overlay Tray provides Restore Normal, opacity, click-through, lock-window, Always on Top, and Mini Mode controls.
- Adds keyboard shortcuts: `F` fit map, `C` center player, `W` clear waypoint, and `T` toggle the side tray.
- Remembers window size/position on close.

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

## Test launch

Without a command window, double-click:

```text
launch_eqgps.pyw
```

The current default test log is:

```text
C:\Users\Public\EQ_P99\Logs\eqlog_Nanantwo_P1999Green 20260604day.txt
```

Map files are expected at:

```text
C:\Users\nanan\Development\EQGPS\map_files
```

Use **Open Log File** in the app to choose a different log. EQGPS stores the last selected file under your Windows roaming AppData EQGPS settings folder.
