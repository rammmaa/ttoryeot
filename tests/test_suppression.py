from pathlib import Path

from ttoryeot.runner import run_workspace

TERMS = "terms:\n  - canonical: 데이터세트\n    aliases: [데이터셋]\n"
MIXED = "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"


def ws(tmp_path: Path, body: str) -> list:
    (tmp_path / "terms.yaml").write_text(TERMS, encoding="utf-8")
    (tmp_path / "a.md").write_text(body, encoding="utf-8")
    return run_workspace(tmp_path, tmp_path / "terms.yaml", {})


def test_baseline_fires_without_pragma(tmp_path):
    assert [d.rule for d in ws(tmp_path, MIXED)] == ["TERM100"]


def test_disable_file_suppresses_everything(tmp_path):
    """prh의 `<!-- prh:disable -->`, Vale의 `<!-- vale off -->` 대응 — 오탐을 문서
    쪽에서 끌 수단이 없으면 사전 기반 규칙은 실사용이 불가능하다."""
    assert ws(tmp_path, "<!-- ttoryeot:disable -->\n\n" + MIXED) == []


def test_disable_file_with_rule_list_is_selective(tmp_path):
    assert ws(tmp_path, "<!-- ttoryeot:disable REF101 -->\n\n" + MIXED) != []
    assert ws(tmp_path, "<!-- ttoryeot:disable TERM100 -->\n\n" + MIXED) == []


def test_disable_next_line(tmp_path):
    body = "데이터세트를 만듭니다.\n\n<!-- ttoryeot:disable-next-line -->\n데이터셋을 저장합니다.\n"
    assert ws(tmp_path, body) == []


def test_pragma_inside_code_fence_is_not_a_pragma(tmp_path):
    """문법을 문서화한 코드블록이 스스로를 억제하면 안 된다 — 실제로 이 저장소의
    README가 자기 진단을 전부 끄고 있었다. 조용한 미탐이라 더 위험하다."""
    body = (
        "````markdown\n<!-- ttoryeot:disable -->\n````\n\n" + MIXED
    )
    assert [d.rule for d in ws(tmp_path, body)] == ["TERM100"]


def test_pragma_inside_inline_code_is_not_a_pragma(tmp_path):
    body = "산문에서 `<!-- ttoryeot:disable -->` 를 설명합니다.\n\n" + MIXED
    assert [d.rule for d in ws(tmp_path, body)] == ["TERM100"]


def test_rule_list_accepts_comma_separation(tmp_path):
    """쉼표 구분은 가장 자연스러운 추측인데 종전엔 통째로 무시되어 아무것도
    억제하지 않았다 — 피드백 없는 실패였다."""
    assert ws(tmp_path, "<!-- ttoryeot:disable TERM100,REF101 -->\n\n" + MIXED) == []


def test_unknown_rule_name_is_reported(tmp_path):
    """오타 난 규칙 이름은 조용히 no-op이 되면 안 된다."""
    diags = ws(tmp_path, "<!-- ttoryeot:disable term100 -->\n\n" + MIXED)
    rules = [d.rule for d in diags]
    assert "INT002" in rules  # 알 수 없는 규칙 이름 경고
    assert "TERM100" in rules  # 억제되지 않고 원 진단도 유지


def test_disable_next_line_only_affects_that_line(tmp_path):
    body = "<!-- ttoryeot:disable-next-line -->\n데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"
    assert [d.rule for d in ws(tmp_path, body)] == ["TERM100"]
