import copy
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """설정 파일을 읽거나 병합할 수 없을 때 — CLI는 이를 exit 2로 변환한다."""


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
        if value is None:
            # YAML의 빈 키(`reference:`)는 '오버라이드 없음'이다 — None으로
            # 섹션을 덮어쓰면 분석기의 dict 병합에서 TypeError가 난다.
            continue
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg = default_config()
    if path is None:
        return cfg
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"설정 파일을 읽을 수 없습니다: {path} ({exc})") from exc
    try:
        user = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"설정 YAML 파싱 실패: {path} ({exc})") from exc
    if user is None:
        return cfg
    if not isinstance(user, dict):
        raise ConfigError(f"설정 최상위는 매핑이어야 합니다: {path}")
    return _deep_merge(cfg, user)
