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


class DocumentIR(BaseModel):
    path: str
    content_hash: str
    blocks: list[Block] = []
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
