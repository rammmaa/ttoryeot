from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import (
    TermEntry,
    build_symbol_table,
    load_term_dictionary,
)
from ttoryeot.parsing.workspace import load_workspace

ENTRIES = [TermEntry(canonical="데이터세트", aliases=["데이터셋", "데이터 세트"])]


def make_ws(tmp_path: Path, files: dict[str, str]):
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def run(ws):
    return list(TermAnalyzer(ENTRIES).analyze(ws, AnalysisContext()))


def test_term100_mixed_in_one_document(tmp_path):
    ws = make_ws(tmp_path, {"a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n"})
    rules = [d.rule for d in run(ws)]
    assert "TERM100" in rules


def test_term101_mixed_across_documents(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n",
        "b.md": "데이터셋을 저장합니다.\n",
    })
    diags = run(ws)
    assert [d.rule for d in diags] == ["TERM101"]
    # 비정본 표기 위치에 진단이 달린다
    assert diags[0].range.file == "b.md"


def test_term102_conflicting_definitions(tmp_path):
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "pipeline.md": "데이터세트란 단일 BigQuery 테이블이다.\n",
    })
    rules = [d.rule for d in run(ws)]
    assert "TERM102" in rules


def test_term100_reported_for_every_mixing_document(tmp_path):
    """여러 문서가 각각 내부 혼용을 갖고 있으면, 첫 문서에서 return 하지 않고
    모든 혼용 문서에 TERM100을, 나머지 순수 비정본 문서에는 TERM101을 보고해야 한다."""
    ws = make_ws(tmp_path, {
        "a.md": "데이터세트를 만듭니다.\n\n데이터셋을 저장합니다.\n",
        "b.md": "데이터세트를 조회합니다.\n\n데이터셋을 삭제합니다.\n",
        "c.md": "데이터셋을 사용합니다.\n",
    })
    diags = run(ws)

    term100_files = {d.range.file for d in diags if d.rule == "TERM100"}
    assert term100_files == {"a.md", "b.md"}

    term101_files = {d.range.file for d in diags if d.rule == "TERM101"}
    assert term101_files == {"c.md"}


def test_term102_identical_definition_is_not_flagged(tmp_path):
    """glossary.md와 정의가 완전히 동일한 문서는 오탐(false positive)이면 안 되고,
    실제로 다른 정의를 가진 문서에만 TERM102가 달려야 한다."""
    ws = make_ws(tmp_path, {
        "glossary.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "guide.md": "데이터세트란 분석 가능한 논리적 테이블의 집합이다.\n",
        "pipeline.md": "데이터세트란 단일 BigQuery 테이블이다.\n",
    })
    diags = run(ws)
    term102 = [d for d in diags if d.rule == "TERM102"]
    assert len(term102) == 1
    assert term102[0].range.file == "pipeline.md"


