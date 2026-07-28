from pathlib import Path

import pytest
import yaml

from ttoryeot.runner import run_workspace

FIXTURES_ROOT = Path("corpus/fixtures")
FIXTURES = sorted(p for p in FIXTURES_ROOT.iterdir() if p.is_dir())


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.name)
def test_golden(fixture: Path):
    expected = yaml.safe_load((fixture / "expected.yaml").read_text(encoding="utf-8"))
    terms = fixture / "terms.yaml"
    # 픽스처별 config.yaml로 opt-in 규칙(TERM104 등)을 켤 수 있다
    config_path = fixture / "config.yaml"
    config = (
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if config_path.exists() else {}
    )
    diags = run_workspace(fixture, terms if terms.exists() else None, config)
    got = {(d.rule, d.range.file, d.range.start_line) for d in diags}
    want = {(e["rule"], e["file"], e["line"]) for e in expected["diagnostics"]}
    assert want <= got, f"missing: {want - got}"
    # clean_files에는 어떤 진단도 없어야 한다 (오탐 체크)
    for clean in expected["clean_files"]:
        assert not [d for d in diags if d.range.file == clean], clean
    # expected에 없는 파일별 초과 진단도 오탐으로 간주
    extra = got - want
    assert not extra, f"unexpected: {extra}"
