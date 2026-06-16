from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import re
import shutil
import zipfile

from .coordinates import raw_map_file_xy_to_map_point

MAP_ARCHIVE_NAME = "map_files.zip"


@dataclass(frozen=True)
class MapLine:
    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float
    color: tuple[int, int, int]


@dataclass(frozen=True)
class MapLabel:
    x: float
    y: float
    z: float
    color: tuple[int, int, int]
    text: str


@dataclass(frozen=True)
class MapLayer:
    name: str
    path: Path


@dataclass
class ParsedMap:
    path: Path
    lines: list[MapLine] = field(default_factory=list)
    labels: list[MapLabel] = field(default_factory=list)

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        xs: list[float] = []
        ys: list[float] = []
        for line in self.lines:
            xs.extend([line.x1, line.x2])
            ys.extend([line.y1, line.y2])
        for label in self.labels:
            xs.append(label.x)
            ys.append(label.y)
        if not xs or not ys:
            return None
        return min(xs), min(ys), max(xs), max(ys)


def visible_color(r: int, g: int, b: int) -> tuple[int, int, int]:
    if r < 32 and g < 32 and b < 32:
        return (220, 220, 220)
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _map_assets_present(map_dir: Path) -> bool:
    return (map_dir / "map_keys.ini").exists() and any(map_dir.glob("*.txt"))


def _safe_archive_target(map_dir: Path, member_name: str) -> Path | None:
    member_path = PurePosixPath(member_name)
    if member_path.is_absolute() or any(part in {"", ".", ".."} for part in member_path.parts):
        return None
    target = map_dir.joinpath(*member_path.parts)
    try:
        target.resolve().relative_to(map_dir.resolve())
    except ValueError:
        return None
    return target


def ensure_map_files_available(map_dir: str | Path) -> bool:
    """Extract bundled map_files.zip when loose map assets are absent.

    Returns True when extraction happened. Returns False when maps were already
    present or no bundled archive exists.
    """
    map_dir = Path(map_dir)
    if _map_assets_present(map_dir):
        return False

    archive_path = map_dir / MAP_ARCHIVE_NAME
    if not archive_path.exists():
        return False

    map_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = _safe_archive_target(map_dir, member.filename)
            if target is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
    return True


def _split_csv(line: str) -> list[str]:
    return [part.strip() for part in line.split(",")]


def parse_map_file(path: str | Path) -> ParsedMap:
    path = Path(path)
    parsed = ParsedMap(path=path)
    if not path.exists():
        return parsed
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or len(line) < 2:
            continue
        record_type = line[0].upper()
        payload = line[1:].strip()
        parts = _split_csv(payload)
        try:
            if record_type == "L" and len(parts) >= 9:
                raw_x1, raw_y1, z1, raw_x2, raw_y2, z2 = (float(parts[i]) for i in range(6))
                p1 = raw_map_file_xy_to_map_point(raw_x1, raw_y1)
                p2 = raw_map_file_xy_to_map_point(raw_x2, raw_y2)
                r, g, b = (int(float(parts[i])) for i in range(6, 9))
                parsed.lines.append(MapLine(p1.x, p1.y, z1, p2.x, p2.y, z2, visible_color(r, g, b)))
            elif record_type in {"P", "T"} and len(parts) >= 7:
                raw_x, raw_y, z = (float(parts[i]) for i in range(3))
                point = raw_map_file_xy_to_map_point(raw_x, raw_y)
                r, g, b = (int(float(parts[i])) for i in range(3, 6))
                text = ",".join(parts[6:]).strip()
                parsed.labels.append(MapLabel(point.x, point.y, z, visible_color(r, g, b), text))
        except ValueError:
            continue
    return parsed


def discover_zone_layers(map_dir: str | Path, zone_key: str) -> list[MapLayer]:
    map_dir = Path(map_dir)
    if not map_dir.exists():
        return []
    wanted = zone_key.lower()
    matches: list[Path] = []
    for path in map_dir.glob("*.txt"):
        stem = path.stem.lower()
        if stem == wanted or re.fullmatch(re.escape(wanted) + r"_\d+", stem):
            matches.append(path)

    def sort_key(path: Path) -> tuple[int, int, str]:
        stem = path.stem.lower()
        if stem == wanted:
            return (0, 0, path.name.lower())
        suffix = stem.rsplit("_", 1)[-1]
        return (1, int(suffix) if suffix.isdigit() else 999, path.name.lower())

    matches.sort(key=sort_key)
    return [MapLayer(name=path.stem, path=path) for path in matches]
