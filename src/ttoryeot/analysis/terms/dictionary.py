from pathlib import Path

import yaml
from pydantic import BaseModel

from ttoryeot.ir.models import WorkspaceIR
from ttoryeot.ir.source import SourceRange


class TermEntry(BaseModel):
    canonical: str
    aliases: list[str] = []
    definition: str | None = None


class TermOccurrence(BaseModel):
    canonical: str
    surface: str
    doc_path: str
    range: SourceRange


def load_term_dictionary(path: Path) -> list[TermEntry]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [TermEntry.model_validate(t) for t in data.get("terms", [])]


def _position(sent_text: str, base_line: int, base_col: int, idx: int) -> tuple[int, int]:
    """문장 시작(base_line/base_col) 기준으로 문장 내 오프셋 idx의 줄·칸을 계산한다.
    sent_text가 원문 슬라이스와 동일하다는 lowering 불변식을 전제하므로 근사가 아니라 정확값이다."""
    newlines = sent_text.count("\n", 0, idx)
    if newlines == 0:
        return base_line, base_col + idx
    last_nl = sent_text.rfind("\n", 0, idx)
    return base_line + newlines, idx - last_nl


def build_symbol_table(
    ws: WorkspaceIR, entries: list[TermEntry]
) -> dict[str, list[TermOccurrence]]:
    table: dict[str, list[TermOccurrence]] = {e.canonical: [] for e in entries}
    surfaces = [
        (e.canonical, s) for e in entries for s in [e.canonical, *e.aliases]
    ]
    # 긴 표면형 우선 매칭 ('데이터 세트'가 '세트'보다 먼저)
    surfaces.sort(key=lambda cs: -len(cs[1]))
    for doc in ws.documents:
        for _doc, _block, sent in WorkspaceIR(root=ws.root, documents=[doc]).iter_sentences():
            taken: list[tuple[int, int]] = []
            for canonical, surface in surfaces:
                start = 0
                while (idx := sent.text.find(surface, start)) != -1:
                    abs_start = sent.range.start_offset + idx
                    abs_end = abs_start + len(surface)
                    start = idx + len(surface)
                    if any(a < abs_end and abs_start < b for a, b in taken):
                        continue
                    taken.append((abs_start, abs_end))
                    sl, sc = _position(sent.text, sent.range.start_line,
                                       sent.range.start_col, idx)
                    el, ec = _position(sent.text, sent.range.start_line,
                                       sent.range.start_col, idx + len(surface))
                    table[canonical].append(TermOccurrence(
                        canonical=canonical, surface=surface, doc_path=doc.path,
                        range=SourceRange(
                            file=doc.path,
                            start_line=sl, start_col=sc,
                            end_line=el, end_col=ec,
                            start_offset=abs_start, end_offset=abs_end,
                        ),
                    ))
    return table
