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
