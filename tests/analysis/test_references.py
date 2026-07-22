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


def test_ref101_considers_antecedents_in_same_sentence(tmp_path):
    ws = make_ws(
        tmp_path,
        "사용자 테이블과 주문 테이블 중 해당 테이블을 선택합니다.\n",
    )

    diags = run(ws)

    assert [d.rule for d in diags] == ["REF101"]
    assert {c.text for c in diags[0].candidates} >= {
        "사용자 테이블",
        "주문 테이블",
    }


def test_same_sentence_support_preserves_prior_sentence_ranking(tmp_path):
    ws = make_ws(
        tmp_path,
        "주문 결과를 확인합니다.\n\n"
        "사용자 결과를 만듭니다.\n\n"
        "해당 결과를 저장합니다.\n",
    )

    assert run(ws) == []


def test_zero_window_excludes_prior_sentences(tmp_path):
    ws = make_ws(
        tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n"
        "해당 데이터를 저장합니다.\n",
    )

    assert run(ws, {"reference": {"window": 0}}) == []


def test_clear_single_candidate_is_silent(tmp_path):
    ws = make_ws(tmp_path, "조인 결과를 만듭니다.\n\n해당 결과를 저장합니다.\n")
    assert run(ws) == []


def test_no_reference_no_diagnostic(tmp_path):
    ws = make_ws(tmp_path, "조인 결과를 저장합니다.\n")
    assert run(ws) == []


