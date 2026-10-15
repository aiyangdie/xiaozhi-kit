"""Load ~/.xzkit/config.toml and project xzkit.toml."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


DEFAULTS: dict[str, Any] = {
    "port": None,
    "baud": 115200,
    "serve_host": "127.0.0.1",
    "serve_port": 8787,
    "presets": {},
}


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data if isinstance(data, dict) else {}


def config_dir() -> Path:
    return Path.home() / ".xzkit"


def user_config_path() -> Path:
    return config_dir() / "config.toml"


def load_config(cwd: Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    user = _load_toml(user_config_path())
    cfg.update({k: v for k, v in user.items() if k in DEFAULTS or k == "presets"})
    if "presets" in user and isinstance(user["presets"], dict):
        cfg["presets"] = {**cfg.get("presets", {}), **user["presets"]}

    root = cwd or Path.cwd()
    project = _load_toml(root / "xzkit.toml")
    for k, v in project.items():
        if k == "presets" and isinstance(v, dict):
            cfg["presets"] = {**cfg.get("presets", {}), **v}
        elif k in DEFAULTS:
            cfg[k] = v
    return cfg
