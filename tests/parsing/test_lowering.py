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


def test_load_workspace_records_parse_error(tmp_path: Path):
    good = tmp_path / "good.md"
    good.write_text("정상 문서입니다.\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe invalid utf8 \xff")
    ws = load_workspace(tmp_path)
    by_path = {d.path: d for d in ws.documents}
    assert by_path["good.md"].parse_error is None
    assert by_path["bad.md"].parse_error is not None
