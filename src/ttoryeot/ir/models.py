import json
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel

from ttoryeot.ir.source import SourceRange


class Token(BaseModel):
    form: str
    tag: str
    range: SourceRange


class NounPhrase(BaseModel):
    text: str
    head: str
    range: SourceRange


class ReferenceExpression(BaseModel):
    text: str
    demonstrative: str
    head: str
    range: SourceRange


class SentenceIR(BaseModel):
    text: str
    range: SourceRange
    tokens: list[Token] = []
    noun_phrases: list[NounPhrase] = []
    references: list[ReferenceExpression] = []


class Block(BaseModel):
    kind: Literal["heading", "paragraph", "list_item", "code_block", "block_quote"]
    level: int | None = None
    range: SourceRange
    sentences: list[SentenceIR] = []


class Suppression(BaseModel):
    """문서에 적힌 진단 억제 지시 (`<!-- ttoryeot:disable [규칙…] -->`).

    prh의 `prh:disable`, Vale의 `vale off`에 대응한다. rules가 비면 전체 규칙.
    scope="file"은 문서 전체, "next_line"은 지시 다음 줄에만 적용된다.
    """

    scope: Literal["file", "next_line"]
    rules: list[str] = []
    line: int


class DocumentIR(BaseModel):
    path: str
    content_hash: str
    blocks: list[Block] = []
    suppressions: list[Suppression] = []
    parse_error: str | None = None


class WorkspaceIR(BaseModel):
    root: str
    documents: list[DocumentIR] = []

    def iter_sentences(self) -> Iterable[tuple[DocumentIR, Block, SentenceIR]]:
        for doc in self.documents:
            for block in doc.blocks:
                for sent in block.sentences:
                    yield doc, block, sent


def export_ir_schema(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "workspace-ir.schema.json").write_text(
        json.dumps(WorkspaceIR.model_json_schema(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
