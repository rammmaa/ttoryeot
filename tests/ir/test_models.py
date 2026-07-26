import json
from pathlib import Path

from ttoryeot.ir.models import (
    Block, DocumentIR, SentenceIR, WorkspaceIR, export_ir_schema,
)
from ttoryeot.ir.source import SourceRange


def rng(f="a.md"):
    return SourceRange(file=f, start_line=1, start_col=1, end_line=1, end_col=10,
                       start_offset=0, end_offset=9)


def test_workspace_iter_sentences():
    sent = SentenceIR(text="문장입니다.", range=rng())
    block = Block(kind="paragraph", range=rng(), sentences=[sent])
    doc = DocumentIR(path="a.md", content_hash="x", blocks=[block])
    ws = WorkspaceIR(root=".", documents=[doc])
    triples = list(ws.iter_sentences())
    assert len(triples) == 1
    assert triples[0][2].text == "문장입니다."


def test_code_block_carries_no_sentences():
    block = Block(kind="code_block", range=rng())
    assert block.sentences == []


def test_export_ir_schema(tmp_path: Path):
    export_ir_schema(tmp_path)
    schema = json.loads((tmp_path / "workspace-ir.schema.json").read_text())
    assert schema["title"] == "WorkspaceIR"
