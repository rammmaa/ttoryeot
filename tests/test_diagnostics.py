from ttoryeot.diagnostics.models import Candidate, Diagnostic
from ttoryeot.ir.source import SourceRange


def rng(**over):
    d = {
        "file": "a.md",
        "start_line": 1,
        "start_col": 1,
        "end_line": 1,
        "end_col": 7,
        "start_offset": 0,
        "end_offset": 6,
    }
    d.update(over)
    return SourceRange(**d)


def test_diagnostic_construction():
    diag = Diagnostic(
        rule="REF101", severity="warning",
        message="'해당 데이터'의 지시 대상이 불명확합니다.",
        range=rng(),
        candidates=[Candidate(text="조인 결과", score=0.48)],
    )
    assert diag.rule == "REF101"
    assert diag.candidates[0].score == 0.48


def test_source_range_ordering_validated():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        rng(end_offset=-1)


def test_protocol_modules_importable():
    from ttoryeot.analysis.base import AnalysisContext, Analyzer
    from ttoryeot.bench.engine import BenchEngine, Prediction

    assert AnalysisContext().config == {}
    assert Prediction(span=(0, 2), category="spacing").category == "spacing"
    assert Analyzer is not None and BenchEngine is not None
