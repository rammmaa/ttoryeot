from pathlib import Path

import yaml

from ttoryeot.runner import run_workspace

FIXTURE = Path("corpus/fixtures/data-platform")


def test_golden_data_platform():
    expected = yaml.safe_load((FIXTURE / "expected.yaml").read_text(encoding="utf-8"))
    diags = run_workspace(FIXTURE, FIXTURE / "terms.yaml", {})
    got = {(d.rule, d.range.file, d.range.start_line) for d in diags}
    want = {(e["rule"], e["file"], e["line"]) for e in expected["diagnostics"]}
    assert want <= got, f"missing: {want - got}"
    # clean_files에는 어떤 진단도 없어야 한다 (오탐 체크)
    for clean in expected["clean_files"]:
        assert not [d for d in diags if d.range.file == clean], clean
    # expected에 없는 파일별 초과 진단도 오탐으로 간주
    extra = got - want
    assert not extra, f"unexpected: {extra}"
