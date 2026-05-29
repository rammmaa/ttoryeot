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


def test_total_aggregates():
    items = [
        item("a", "리쿠르팅 존", [ann((0, 4))]),
        item("b", "정상 문장입니다.", []),
    ]
    preds = {
        "a": [Prediction(span=(0, 4), category="loanword_spelling")],
        "b": [Prediction(span=(0, 2), category="spacing")],
    }
    total = score_items(items, preds)["__total__"]
    assert (total.tp, total.fp, total.fn) == (1, 1, 0)


def test_zero_division_guard():
    s = RuleScore(tp=0, fp=0, fn=0)
    assert s.precision == 0.0 and s.recall == 0.0 and s.f1 == 0.0


def test_optimal_matching_beats_greedy():
    """Counterexample to greedy matching: overlapping spans in same category.

    ann1=(0, 20), ann2=(15, 25) both span-overlap with pred_a=(15,25) and pred_b=(0,10)
    Greedy with pred=[a, b]: ann1 takes pred_a → ann2 tries pred_a (taken), tries pred_b (no overlap) → tp=1, fp=1, fn=1
    Optimal: ann1↔pred_b, ann2↔pred_a → tp=2, fp=0, fn=0
    """
    text = "리쿠르팅리쿠르팅리쿠르팅리쿠르팅리쿠르팅리쿠르팅리쿠르팅"  # 28 chars
    items = [
        item(
            "a",
            text,
            [ann((0, 20), "loanword_spelling"), ann((15, 25), "loanword_spelling")],
        )
    ]
    preds = {
        "a": [
            Prediction(span=(15, 25), category="loanword_spelling"),  # pred_a
            Prediction(span=(0, 10), category="loanword_spelling"),   # pred_b
        ]
    }
    s = score_items(items, preds)["loanword_spelling"]
    # With greedy: tp=1 (ann1 takes pred_a), fp=1 (pred_b unmatched), fn=1 (ann2 unmatched)
    # With optimal: tp=2, fp=0, fn=0
    assert (s.tp, s.fp, s.fn) == (2, 0, 0), "Optimal matching should find 2 TPs"


