from dataclasses import dataclass

from markdown_it import MarkdownIt

_KIND_BY_TOKEN = {
    "heading_open": "heading",
    "paragraph_open": "paragraph",
    "blockquote_open": "block_quote",
}


@dataclass
class RawBlock:
    kind: str
    level: int | None
    text: str
    start_line: int  # 1-based
    end_line: int
    start_offset: int  # source 기준 0-based


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def parse_blocks(source: str) -> list[RawBlock]:
    md = MarkdownIt("commonmark")
    tokens = md.parse(source)
    line_offsets = _line_offsets(source)
    lines = source.split("\n")
    blocks: list[RawBlock] = []
    in_list_item = False

    for i, tok in enumerate(tokens):
        if tok.type == "list_item_open":
            in_list_item = True
            continue
        if tok.type == "list_item_close":
            in_list_item = False
            continue
        if tok.type == "fence" and tok.map:
            start, end = tok.map
            blocks.append(RawBlock(
                kind="code_block", level=None, text="",
                start_line=start + 1, end_line=end,
                start_offset=line_offsets[start],
            ))
            continue
        kind = _KIND_BY_TOKEN.get(tok.type)
        if kind is None or not tok.map:
            continue
        if kind == "paragraph" and in_list_item:
            kind = "list_item"
        start, end = tok.map

        # 원문 슬라이스 불변식을 위해 tok.map 라인 범위를 그대로 이어 붙인다.
        # source.split("\n") 후 다시 "\n".join 하면 원문의 해당 구간과 항상
        # 정확히 일치한다 (split/join은 서로 역연산).
        raw = "\n".join(lines[start:end])
        block_start_offset = line_offsets[start]

        level = int(tok.tag[1:]) if kind == "heading" and tok.tag[:1] == "h" else None

        # markdown-it이 이미 계산해 둔 inline 토큰의 content는 인라인 마크업은
        # 보존한 채(=제거하지 않은 채) 블록 마커(#, >, -, 들여쓰기 등)만 걷어낸
        # 문자열이다. 이를 raw 안에서 찾아 위치를 역산하면, 마커 종류마다
        # 오프셋 계산 규칙을 직접 재구현하지 않고도 불변식을 만족시킬 수 있다.
        inline = tokens[i + 1] if i + 1 < len(tokens) else None
        if inline is not None and inline.type == "inline":
            content = inline.content
            idx = raw.find(content) if content else 0
            if idx == -1:
                # 방어적 fallback: 원문에서 못 찾으면 가공 없이 raw 전체를 사용한다.
                text = raw
                start_offset = block_start_offset
            else:
                text = content
                start_offset = block_start_offset + idx
        else:
            text = raw
            start_offset = block_start_offset

        blocks.append(RawBlock(
            kind=kind, level=level, text=text,
            start_line=start + 1, end_line=end,
            start_offset=start_offset,
        ))
    return blocks
