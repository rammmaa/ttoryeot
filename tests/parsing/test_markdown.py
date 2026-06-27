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


