from __future__ import annotations

import json
from pathlib import Path


DEFAULT_CONFIG: dict[str, object] = {
    "schema_version": "1.0.0",
    "atomic_notes_folder": "Atomic Notes",
    "structure_notes_folder": "Structure Notes",
    "atomic_note_template": "Templates/Atomic Note Template.md",
    "audit_output_folder": "Reviews/Atomic Note Audits",
}


def resolve_config(vault_root: Path) -> dict[str, object]:
    config = dict(DEFAULT_CONFIG)
    config_path = vault_root / ".networked-thinking" / "config.json"
    if config_path.exists():
        overrides = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(overrides, dict):
            raise ValueError(f"{config_path} must contain a JSON object")
        config.update(overrides)
    return config
