from ttoryeot.bench.baselines import (
    NaiveReferenceBaseline,
    RegexBaseline,
    SubstitutionBaseline,
)
from ttoryeot.bench.schema import SentenceItem


def item(text: str, ctx: str = "") -> SentenceItem:
    return SentenceItem(
        id="t", source="test", document_type="fixture",
        context_before=ctx, text=text,
    )


def test_substitution_finds_loanword():
    preds = SubstitutionBaseline().predict(item("리쿠르팅 존을 준비합니다."))
    assert len(preds) == 1
    assert preds[0].category == "loanword_spelling"
    assert preds[0].span == (0, 4)  # '리쿠르팅'


def test_substitution_clean_text_no_prediction():
    assert SubstitutionBaseline().predict(item("리크루팅 존을 준비합니다.")) == []


