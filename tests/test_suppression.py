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


def test_disable_next_line_only_affects_that_line(tmp_path):
    body = "<!-- ttoryeot:disable-next-line -->\n데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"
    assert [d.rule for d in ws(tmp_path, body)] == ["TERM100"]
