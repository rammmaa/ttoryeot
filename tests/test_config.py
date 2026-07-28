from ttoryeot.config import default_config, load_config


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


def test_code_defaults_are_sourced_from_yaml():
    """드리프트 가드 — 분석기가 빈 컨텍스트에서 쓰는 기본값과 후보 랭킹 가중치는
    default.yaml에서 와야 한다. YAML만 바꿔도 코드 기본값이 따라와야 한다."""
    from ttoryeot.analysis.references import analyzer, candidates

    ref = default_config()["reference"]
    assert candidates.DEFAULT_WEIGHTS == ref["weights"]
    assert analyzer.DEFAULTS["window"] == ref["window"]
    assert analyzer.DEFAULTS["threshold"] == ref["threshold"]
