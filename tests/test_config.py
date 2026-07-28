import pytest

from ttoryeot.config import ConfigError, default_config, load_config


def test_default_config_has_reference_section():
    ref = default_config()["reference"]
    assert set(ref) >= {"window", "threshold", "weights"}
    assert set(ref["weights"]) == {"distance", "role", "head_match", "recency"}


def test_default_config_returns_fresh_copy():
    default_config()["reference"]["window"] = 999
    assert default_config()["reference"]["window"] != 999


def test_load_config_without_path_is_default():
    assert load_config() == default_config()


def test_load_config_deep_merges_override(tmp_path):
    override = tmp_path / "override.yaml"
    override.write_text("reference:\n  threshold: 0.5\n", encoding="utf-8")
    cfg = load_config(override)
    assert cfg["reference"]["threshold"] == 0.5
    # 오버라이드하지 않은 키는 기본값 유지
    assert cfg["reference"]["window"] == default_config()["reference"]["window"]
    assert cfg["reference"]["weights"] == default_config()["reference"]["weights"]


def test_load_config_missing_file_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_load_config_malformed_yaml_raises_config_error(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("reference: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_load_config_non_mapping_raises_config_error(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_load_config_null_section_keeps_defaults(tmp_path):
    """자식을 전부 주석 처리해 `reference:`만 남긴 설정은 '오버라이드 없음'이어야
    한다 — None이 섹션을 덮어쓰면 분석기에서 TypeError가 난다 (리뷰 지적 재현)."""
    p = tmp_path / "null.yaml"
    p.write_text("reference:\n", encoding="utf-8")
    assert load_config(p) == default_config()


def test_code_defaults_are_sourced_from_yaml():
    """드리프트 가드 — 분석기가 빈 컨텍스트에서 쓰는 기본값과 후보 랭킹 가중치는
    default.yaml에서 와야 한다. YAML만 바꿔도 코드 기본값이 따라와야 한다."""
    from ttoryeot.analysis.references import analyzer, candidates

    ref = default_config()["reference"]
    assert candidates.DEFAULT_WEIGHTS == ref["weights"]
    assert analyzer.DEFAULTS["window"] == ref["window"]
    assert analyzer.DEFAULTS["threshold"] == ref["threshold"]
