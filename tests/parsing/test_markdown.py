from ttoryeot.parsing.markdown import parse_blocks

SOURCE = """# 제목입니다

첫 문단입니다. 두 번째 문장입니다.

```python
code = "무시해야 합니다"
```

- 목록 항목입니다
"""


def test_parses_block_kinds():
    kinds = [b.kind for b in parse_blocks(SOURCE)]
    assert kinds == ["heading", "paragraph", "code_block", "list_item"]


def test_heading_level_and_text():
    heading = parse_blocks(SOURCE)[0]
    assert heading.level == 1
    assert heading.text == "제목입니다"


def test_paragraph_text_is_source_slice():
    para = parse_blocks(SOURCE)[1]
    assert para.text == "첫 문단입니다. 두 번째 문장입니다."
    # 원문 슬라이스 불변식: start_offset부터 text가 원문과 일치
    assert SOURCE[para.start_offset : para.start_offset + len(para.text)] == para.text


def test_code_block_text_empty():
    code = parse_blocks(SOURCE)[2]
    assert code.text == ""


BLOCKQUOTE_SOURCE = """> 인용 문단입니다.

일반 문단입니다.
"""


def test_blockquote_is_position_only_container():
    blocks = parse_blocks(BLOCKQUOTE_SOURCE)
    kinds = [b.kind for b in blocks]
    assert kinds == ["block_quote", "paragraph", "paragraph"]

    block_quote = blocks[0]
    assert block_quote.text == ""

    inner_paragraph = blocks[1]
    assert inner_paragraph.text == "인용 문단입니다."
    # 원문 슬라이스 불변식: start_offset부터 text가 원문과 일치
    assert (
        BLOCKQUOTE_SOURCE[
            inner_paragraph.start_offset : inner_paragraph.start_offset
            + len(inner_paragraph.text)
        ]
        == inner_paragraph.text
    )

    # 인용문 내용을 담은 블록은 정확히 하나뿐이어야 한다 (이중 방출 금지)
    non_empty = [b for b in blocks if b.text and "인용 문단입니다" in b.text]
    assert len(non_empty) == 1


def test_multiline_blockquote_preserves_clean_source_slices():
    source = "> 첫 줄입니다.\n> 둘째 줄입니다.\n"

    paragraphs = [b for b in parse_blocks(source) if b.kind == "paragraph"]

    assert [b.text for b in paragraphs] == ["첫 줄입니다.", "둘째 줄입니다."]
    for paragraph in paragraphs:
        assert (
            source[
                paragraph.start_offset : paragraph.start_offset
                + len(paragraph.text)
            ]
            == paragraph.text
        )
