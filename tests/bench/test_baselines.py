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


def test_regex_finds_spacing():
    preds = RegexBaseline().predict(item("배포를 준비중입니다."))
    assert preds and preds[0].category == "spacing"


def test_naive_ref_fires_on_any_demonstrative():
    preds = NaiveReferenceBaseline().predict(item("해당 데이터를 저장합니다."))
    assert preds and preds[0].category == "ambiguous_reference"
    assert preds[0].span == (0, 7)  # '해당 데이터를' — 나이브 매칭은 조사 포함


