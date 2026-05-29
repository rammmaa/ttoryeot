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


def test_wrong_span_is_fp_and_fn():
    items = [item("a", "리쿠르팅 존을 봅니다", [ann((0, 4))])]
    preds = {"a": [Prediction(span=(8, 10), category="loanword_spelling")]}
    s = score_items(items, preds)["loanword_spelling"]
    assert (s.tp, s.fp, s.fn) == (0, 1, 1)


def test_prediction_on_negative_example_is_fp():
    items = [item("a", "정상 문장입니다.", [])]
    preds = {"a": [Prediction(span=(0, 2), category="spacing")]}
    s = score_items(items, preds)["spacing"]
    assert (s.tp, s.fp, s.fn) == (0, 1, 0)


def test_missed_annotation_is_fn():
    items = [item("a", "리쿠르팅 존", [ann((0, 4))])]
    s = score_items(items, {"a": []})["loanword_spelling"]
    assert (s.tp, s.fp, s.fn) == (0, 0, 1)


