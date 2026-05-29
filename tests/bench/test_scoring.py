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


def test_exact_match_is_tp():
    items = [item("a", "리쿠르팅 존", [ann((0, 4))])]
    preds = {"a": [Prediction(span=(0, 4), category="loanword_spelling")]}
    s = score_items(items, preds)["loanword_spelling"]
    assert (s.tp, s.fp, s.fn) == (1, 0, 0)
    assert s.precision == 1.0 and s.recall == 1.0


