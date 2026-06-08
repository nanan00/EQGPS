from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def normalize_zone_name(name: str) -> str:
    return " ".join(name.strip().strip('"\'').lower().rstrip(".").strip().split())


def _read_key_file(path: str | Path) -> dict[str, str]:
    path = Path(path)
    entries: dict[str, str] = {}
    if not path.exists():
        return entries
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if "=" not in line:
            continue
        left, right = line.split("=", 1)
        entries[normalize_zone_name(left)] = right.strip()
    return entries


@dataclass(frozen=True)
class MapKeys:
    entries: dict[str, str]
    aliases: dict[str, str]

    @classmethod
    def load(cls, path: str | Path, who_alias_path: str | Path | None = None) -> "MapKeys":
        entries = _read_key_file(path)
        aliases = _read_key_file(who_alias_path) if who_alias_path is not None else {}
        return cls(entries, aliases)

    def resolve(self, zone_name: str) -> str | None:
        normalized = normalize_zone_name(zone_name)
        direct = self.entries.get(normalized)
        if direct:
            return direct
        alias_target = self.aliases.get(normalized)
        if not alias_target:
            return None
        return self.entries.get(normalize_zone_name(alias_target))

    def resolve_canonical_name(self, zone_name: str) -> str | None:
        """Return the canonical map_keys.ini zone name when resolved through map_keys_who.ini."""
        normalized = normalize_zone_name(zone_name)
        if normalized in self.entries:
            return zone_name.strip().rstrip(".")
        return self.aliases.get(normalized)
