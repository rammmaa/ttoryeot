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


def test_load_workspace_records_parse_error(tmp_path: Path):
    good = tmp_path / "good.md"
    good.write_text("정상 문서입니다.\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe invalid utf8 \xff")
    ws = load_workspace(tmp_path)
    by_path = {d.path: d for d in ws.documents}
    assert by_path["good.md"].parse_error is None
    assert by_path["bad.md"].parse_error is not None
