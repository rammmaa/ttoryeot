from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.parsing.workspace import load_workspace


def make_ws(tmp_path: Path, content: str):
    (tmp_path / "doc.md").write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def run(ws, config=None):
    ctx = AnalysisContext(config=config or {})
    return list(ReferenceAnalyzer().analyze(ws, ctx))


def test_ref101_on_ambiguous_reference(tmp_path):
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    diags = run(ws)
    assert [d.rule for d in diags] == ["REF101"]
    assert len(diags[0].candidates) >= 2


