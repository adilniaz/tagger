from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "tagger" / "settings.json"

EXTENDED_FIELDS = ["albumartist", "discnumber", "composer", "comment", "lyrics"]


@dataclass
class Settings:
    enabled_extended: set[str] = field(default_factory=set)

    @classmethod
    def load(cls) -> Settings:
        if not CONFIG_PATH.exists():
            return cls()
        data = json.loads(CONFIG_PATH.read_text())
        return cls(enabled_extended=set(data.get("extended_fields", [])))

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps({"extended_fields": sorted(self.enabled_extended)}, indent=2)
        )
