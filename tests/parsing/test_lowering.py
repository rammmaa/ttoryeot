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


