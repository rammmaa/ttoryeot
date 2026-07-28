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


def test_substitution_covers_audit_bulk_replacements():
    """조사표 '일괄 치환 후보' 시트(2026-07-26)가 치환 베이스라인에 반영되어야 한다 —
    감사자가 전역 치환 안전으로 판정한 목록이 이 베이스라인의 정의다."""
    b = SubstitutionBaseline()
    loan = b.predict(item("워크샵을 준비하며 컨텐츠를 만들었어요."))
    assert len(loan) == 2
    assert {p.category for p in loan} == {"loanword_spelling"}
    spacing = b.predict(item("신규입사자와 문화의날 행사"))
    assert len(spacing) == 2
    assert {p.category for p in spacing} == {"spacing"}
    ending = b.predict(item("분위기가 좋더라구요."))
    assert {p.category for p in ending} == {"grammar_agreement"}


def test_regex_finds_spacing():
    preds = RegexBaseline().predict(item("배포를 준비중입니다."))
    assert preds and preds[0].category == "spacing"


def test_naive_ref_fires_on_any_demonstrative():
    preds = NaiveReferenceBaseline().predict(item("해당 데이터를 저장합니다."))
    assert preds and preds[0].category == "ambiguous_reference"
    assert preds[0].span == (0, 7)  # '해당 데이터를' — 나이브 매칭은 조사 포함


def test_naive_ref_silent_without_demonstrative():
    assert NaiveReferenceBaseline().predict(item("조인 결과를 저장합니다.")) == []
