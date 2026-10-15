"""Named shortcut commands for debugging Xiaozhi boards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_config

BUILTIN: dict[str, str] = {
    "ping": "ping",
    "help": "help",
    "reboot": "reboot",
}


def list_presets(cwd: Path | None = None) -> dict[str, str]:
    cfg = load_config(cwd)
    merged = {**BUILTIN, **(cfg.get("presets") or {})}
    return {str(k): str(v) for k, v in merged.items()}


def get_preset(name: str, cwd: Path | None = None) -> str | None:
    return list_presets(cwd).get(name)


def presets_payload(cwd: Path | None = None) -> dict[str, Any]:
    items = list_presets(cwd)
    return {
        "ok": True,
        "presets": [{"name": k, "text": v} for k, v in sorted(items.items())],
    }
