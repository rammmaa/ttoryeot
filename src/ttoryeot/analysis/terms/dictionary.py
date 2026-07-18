from pathlib import Path

import yaml
from pydantic import BaseModel

from ttoryeot.ir.models import SentenceIR, WorkspaceIR
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


def _sentence_position(sent: SentenceIR, offset: int) -> tuple[int, int]:
    prefix = sent.text[:offset]
    line = sent.range.start_line + prefix.count("\n")
    if "\n" in prefix:
        column = len(prefix.rsplit("\n", 1)[-1]) + 1
    else:
        column = sent.range.start_col + len(prefix)
    return line, column


def load_term_dictionary(path: Path) -> list[TermEntry]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [TermEntry.model_validate(t) for t in data.get("terms", [])]


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
                    start_line, start_col = _sentence_position(sent, idx)
                    end_line, end_col = _sentence_position(
                        sent,
                        idx + len(surface),
                    )
                    table[canonical].append(TermOccurrence(
                        canonical=canonical, surface=surface, doc_path=doc.path,
                        range=SourceRange(
                            file=doc.path,
                            start_line=start_line, start_col=start_col,
                            end_line=end_line, end_col=end_col,
                            start_offset=abs_start, end_offset=abs_end,
                        ),
                    ))
    return table
