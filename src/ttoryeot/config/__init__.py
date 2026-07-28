import copy
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


@cache
def _packaged_default() -> dict[str, Any]:
    text = (resources.files("ttoryeot.config") / "default.yaml").read_text(
        encoding="utf-8"
    )
    return yaml.safe_load(text)


def default_config() -> dict[str, Any]:
    return copy.deepcopy(_packaged_default())


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg = default_config()
    if path is not None:
        user = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cfg = _deep_merge(cfg, user)
    return cfg
