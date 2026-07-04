from pathlib import Path

from kiwipiepy import Kiwi

from ttoryeot.ir.models import DocumentIR, WorkspaceIR
from ttoryeot.parsing.lowering import lower_document

_kiwi: Kiwi | None = None


def get_kiwi() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        _kiwi = Kiwi()
    return _kiwi


def load_workspace(root: Path) -> WorkspaceIR:
    kiwi = get_kiwi()
    documents = []
    for md_path in sorted(root.rglob("*.md")):
        rel = str(md_path.relative_to(root))
        try:
            source = md_path.read_text(encoding="utf-8")
            documents.append(lower_document(rel, source, kiwi))
        except Exception as exc:  # noqa: BLE001 - isolate per-document failures
            documents.append(DocumentIR(path=rel, content_hash="", parse_error=str(exc)))
    return WorkspaceIR(root=str(root), documents=documents)
