from ttoryeot.bench.adapter import TtoryeotEngine
from ttoryeot.bench.schema import SentenceItem


def item(text, ctx=""):
    return SentenceItem(id="t", source="t", document_type="f",
                        context_before=ctx, text=text)


def test_predicts_ambiguous_reference_within_text_span():
    preds = TtoryeotEngine().predict(item(
        "해당 데이터를 저장합니다.",
        ctx="사용자 테이블과 주문 테이블을 조인합니다.",
    ))
    assert len(preds) == 1
    p = preds[0]
    assert p.category == "ambiguous_reference"
    assert p.span == (0, 6)  # text 기준 '해당 데이터'


