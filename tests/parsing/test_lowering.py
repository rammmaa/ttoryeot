from pathlib import Path

from kiwipiepy import Kiwi

from ttoryeot.parsing.lowering import lower_document
from ttoryeot.parsing.workspace import load_workspace

KIWI = Kiwi()

SOURCE = """# 파이프라인

사용자 테이블과 주문 테이블을 조인합니다. 해당 데이터를 저장합니다.
"""


def test_sentences_split():
    doc = lower_document("a.md", SOURCE, KIWI)
    para = doc.blocks[1]
    assert len(para.sentences) == 2


def test_sentence_offsets_roundtrip():
    doc = lower_document("a.md", SOURCE, KIWI)
    for block in doc.blocks:
        for sent in block.sentences:
            sliced = SOURCE[sent.range.start_offset : sent.range.end_offset]
            assert sliced == sent.text


def test_noun_phrases_extracted():
    doc = lower_document("a.md", SOURCE, KIWI)
    first = doc.blocks[1].sentences[0]
    heads = [np.head for np in first.noun_phrases]
    assert "테이블" in heads


def test_reference_expression_extracted():
    doc = lower_document("a.md", SOURCE, KIWI)
    second = doc.blocks[1].sentences[1]
    assert len(second.references) == 1
    ref = second.references[0]
    assert ref.demonstrative == "해당" and ref.head == "데이터"
    assert SOURCE[ref.range.start_offset : ref.range.end_offset] == ref.text


def test_inline_code_masked_from_kiwi():
    """스펙 §5 — 인라인 코드는 Kiwi 분석에서 제외한다. 식별자가 명사구 후보로
    유입되지 않아야 한다. 마스킹은 길이 보존 공백 치환이라 오프셋 불변식은 유지된다."""
    doc = lower_document("a.md", "`user_table` 이 테이블을 조인한다.\n", KIWI)
    phrases = [np.text for b in doc.blocks for s in b.sentences for np in s.noun_phrases]
    joined = " ".join(phrases)
    assert "user" not in joined and "table" not in joined
    assert "테이블" in phrases  # 코드 밖 명사는 유지


def test_inline_code_masked_as_dummy_noun_preserves_structure():
    """LTeX+의 dummy 치환 — 코드를 공백으로 지우면 문장 구조가 깨져 뒤 명사구의
    문법역 판정이 어긋난다. 같은 길이의 더미 명사로 채우면 구조가 살아 후보 랭킹이
    안정된다 (길이는 여전히 보존되므로 오프셋 불변식은 그대로)."""
    doc = lower_document("a.md", "`user_table`이 주문 테이블을 참조합니다.\n", KIWI)
    sent = doc.blocks[0].sentences[0]
    # 코드 뒤 주격 조사 '이'가 조사로 인식되어야 한다 (공백 뒤에 고아로 남으면 안 됨)
    assert any(t.form == "이" and t.tag.startswith("J") for t in sent.tokens)
    phrases = " ".join(np.text for np in sent.noun_phrases)
    assert "user_table" not in phrases


def test_dot_inside_inline_code_does_not_split_sentence():
    doc = lower_document("a.md", "실행은 `run(). stop()` 다음에 한다.\n", KIWI)
    sents = [s for b in doc.blocks for s in b.sentences]
    assert len(sents) == 1
    assert sents[0].text == "실행은 `run(). stop()` 다음에 한다."


def test_midword_determiner_is_not_a_reference():
    """Kiwi가 미등록 외래어를 오분해하며 단어 중간에 만든 이/MM(예: '메모이제이션' →
    메모+이제+이/MM+션/NNP)은 지시어가 아니다 — 지시 관형사는 단어 경계에서만 시작한다.
    (외부 코퍼스 측정에서 REF101 오탐 클러스터로 실측된 사례. Kiwi 분해는 문맥
    의존이라 이 문장은 오분해가 재현되는 최소 사례다 — '…은 성능에 좋다'로 바꾸면
    통짜 NNP로 분석되어 테스트가 무의미해진다.)"""
    doc = lower_document("a.md", "메모이제이션은 좋다.\n", KIWI)
    tokens = doc.blocks[0].sentences[0].tokens
    assert any(t.form == "이" and t.tag in ("MM", "MMD") for t in tokens), (
        "전제 붕괴: Kiwi 모델이 이 문장을 더 이상 오분해하지 않는다 — "
        "단어 중간 이/MM이 재현되는 새 문장을 찾아 테스트를 갱신하라"
    )
    refs = [r for b in doc.blocks for s in b.sentences for r in s.references]
    assert refs == []


def test_determiner_reference_at_word_boundary_still_extracted():
    doc = lower_document("a.md", "주문 테이블이 있다. 이 테이블을 조인한다.\n", KIWI)
    refs = [r for b in doc.blocks for s in b.sentences for r in s.references]
    assert [r.text for r in refs] == ["이 테이블"]


BLOCKQUOTE_SOURCE = """# 제목

> 인용된 문장입니다.
"""


def test_blockquote_sentence_emitted_exactly_once():
    doc = lower_document("a.md", BLOCKQUOTE_SOURCE, KIWI)
    all_texts = [
        sent.text for block in doc.blocks for sent in block.sentences
    ]
    # "> " 마커가 붙은 컨테이너 블록에서 한 번, 내부 문단에서 한 번씩
    # 이중으로 방출되면 안 된다 (마커 유무와 무관하게 내용 기준으로 유일해야 함).
    matching = [t for t in all_texts if "인용된 문장입니다" in t]
    assert len(matching) == 1
    assert matching[0] == "인용된 문장입니다."


CODE_DENSE_SOURCE = """# `run()` 사용법

`user_table` 과 `order_table` 을 `join()` 으로 합칩니다. 결과는 `df.save()` 로 저장합니다.

- `config.yaml` 의 `threshold` 값을 조정합니다.

> 예외는 `try: run()` 블록에서 잡습니다. 이 값은 `None` 이 됩니다.
"""


def test_roundtrip_holds_in_code_dense_document():
    """마스킹×오프셋 상호작용의 영구 고정. 슬라이스==텍스트 단언은 구성상 항등에
    가깝고, 실제 하중은 마지막의 식별자 부재 단언이 진다 — 명사 런이 마스킹 영역을
    건너뛰어 병합되면 구 텍스트에 코드가 재유입되는 결함을 이 단언이 적발했다."""
    doc = lower_document("a.md", CODE_DENSE_SOURCE, KIWI)
    n_sent = 0
    for block in doc.blocks:
        for sent in block.sentences:
            n_sent += 1
            assert CODE_DENSE_SOURCE[sent.range.start_offset:sent.range.end_offset] == sent.text
            for np in sent.noun_phrases:
                assert CODE_DENSE_SOURCE[np.range.start_offset:np.range.end_offset] == np.text
            for ref in sent.references:
                assert CODE_DENSE_SOURCE[ref.range.start_offset:ref.range.end_offset] == ref.text
    assert n_sent >= 4
    phrases = " ".join(
        np.text for b in doc.blocks for s in b.sentences for np in s.noun_phrases
    )
    for ident in ("user_table", "order_table", "join", "config", "threshold", "None"):
        assert ident not in phrases  # 코드 식별자는 후보 우주에 없다


def test_load_workspace_records_parse_error(tmp_path: Path):
    good = tmp_path / "good.md"
    good.write_text("정상 문서입니다.\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe invalid utf8 \xff")
    ws = load_workspace(tmp_path)
    by_path = {d.path: d for d in ws.documents}
    assert by_path["good.md"].parse_error is None
    assert by_path["bad.md"].parse_error is not None
