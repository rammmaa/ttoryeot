import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, field_validator

from ttoryeot.ir.models import SentenceIR, WorkspaceIR
from ttoryeot.ir.source import SourceRange

# 표기 상태 축. ISO 704(preferred/admitted), TBX administrativeStatus,
# SKOS altLabel(정상 이표기) vs hiddenLabel(감출 표기)이 공통으로 갖는 구분이다.
# 이 축이 없으면 '써도 되는 이표기'를 사전에 적는 순간 TERM104 오탐이 된다.
TermStatus = Literal["admitted", "deprecated"]


class TermAlias(BaseModel):
    surface: str
    status: TermStatus = "deprecated"
    note: str | None = None


class TermEntry(BaseModel):
    canonical: str
    aliases: list[TermAlias] = []
    definition: str | None = None

    @field_validator("aliases", mode="before")
    @classmethod
    def _coerce_aliases(cls, value: Any) -> Any:
        # 문자열 alias는 기존 동작(비권장 표기)으로 해석 — 하위 호환
        if isinstance(value, list):
            return [{"surface": a} if isinstance(a, str) else a for a in value]
        return value

    def surfaces(self) -> list[tuple[str, TermStatus]]:
        return [(self.canonical, "admitted")] + [
            (a.surface, a.status) for a in self.aliases
        ]


class TermOccurrence(BaseModel):
    canonical: str
    surface: str
    status: TermStatus = "admitted"
    doc_path: str
    range: SourceRange


def load_term_dictionary(path: Path) -> list[TermEntry]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [TermEntry.model_validate(t) for t in data.get("terms", [])]


def position_in_sentence(
    sent_text: str, base_line: int, base_col: int, idx: int
) -> tuple[int, int]:
    """문장 시작(base_line/base_col) 기준으로 문장 내 오프셋 idx의 줄·칸을 계산한다.
    sent_text가 원문 슬라이스와 동일하다는 lowering 불변식을 전제하므로 근사가 아니라 정확값이다."""
    newlines = sent_text.count("\n", 0, idx)
    if newlines == 0:
        return base_line, base_col + idx
    last_nl = sent_text.rfind("\n", 0, idx)
    return base_line + newlines, idx - last_nl


_WORD_CHAR = re.compile(r"[0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ]")


def _is_eojeol_match(sent: SentenceIR, idx: int, length: int) -> bool:
    """어절 경계 매칭인지 판정한다.

    Kiwi는 복합명사를 형태소로 쪼개므로('데이터세트' → 데이터+세트) 토큰 경계만
    보면 '세트'가 '데이터세트' 안에서 매칭된다. 한국어에서 독립 단어 출현의 단위는
    어절이므로 어절 시작을 요구하되, 뒤에 붙는 조사(J*)는 허용한다.
    """
    text = sent.text
    if idx > 0 and _WORD_CHAR.match(text[idx - 1]):
        return False
    end = idx + length
    if end >= len(text) or not _WORD_CHAR.match(text[end]):
        return True
    # 같은 어절 안에서 이어지는 부분은 조사만 허용한다
    eojeol_end = end
    while eojeol_end < len(text) and not text[eojeol_end].isspace():
        eojeol_end += 1
    base = sent.range.start_offset
    tail = [
        t for t in sent.tokens
        if base + end <= t.range.start_offset < base + eojeol_end
    ]
    return bool(tail) and all(t.tag.startswith("J") for t in tail)


def build_symbol_table(
    ws: WorkspaceIR, entries: list[TermEntry]
) -> dict[str, list[TermOccurrence]]:
    table: dict[str, list[TermOccurrence]] = {e.canonical: [] for e in entries}
    surfaces = [
        (e.canonical, surface, status)
        for e in entries
        for surface, status in e.surfaces()
    ]
    # 긴 표면형 우선 매칭 ('데이터 세트'가 '세트'보다 먼저)
    surfaces.sort(key=lambda cs: -len(cs[1]))
    for doc in ws.documents:
        for _doc, _block, sent in WorkspaceIR(root=ws.root, documents=[doc]).iter_sentences():
            taken: list[tuple[int, int]] = []
            for canonical, surface, status in surfaces:
                start = 0
                while (idx := sent.text.find(surface, start)) != -1:
                    abs_start = sent.range.start_offset + idx
                    abs_end = abs_start + len(surface)
                    start = idx + len(surface)
                    if any(a < abs_end and abs_start < b for a, b in taken):
                        continue
                    if not _is_eojeol_match(sent, idx, len(surface)):
                        continue
                    taken.append((abs_start, abs_end))
                    sl, sc = position_in_sentence(sent.text, sent.range.start_line,
                                       sent.range.start_col, idx)
                    el, ec = position_in_sentence(sent.text, sent.range.start_line,
                                       sent.range.start_col, idx + len(surface))
                    table[canonical].append(TermOccurrence(
                        canonical=canonical, surface=surface, status=status,
                        doc_path=doc.path,
                        range=SourceRange(
                            file=doc.path,
                            start_line=sl, start_col=sc,
                            end_line=el, end_col=ec,
                            start_offset=abs_start, end_offset=abs_end,
                        ),
                    ))
    return table
