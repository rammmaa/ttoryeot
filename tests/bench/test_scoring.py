from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.schema import Annotation, SentenceItem
from ttoryeot.bench.scoring import RuleScore, score_items, spans_overlap


def ann(span, category="loanword_spelling"):
    return Annotation(span=span, category=category, severity="warning", confidence="high")


def item(id, text, anns):
    return SentenceItem(id=id, source="t", document_type="f", text=text, annotations=anns)


def test_spans_overlap():
    assert spans_overlap((0, 5), (4, 9))
    assert not spans_overlap((0, 5), (5, 9))


