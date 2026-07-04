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


