from pathlib import Path
from typing import Any

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import load_term_dictionary
from ttoryeot.diagnostics.models import Diagnostic
from ttoryeot.ir.source import SourceRange
from ttoryeot.parsing.workspace import load_workspace


def run_workspace(
    root: Path, terms_path: Path | None, config: dict[str, Any]
) -> list[Diagnostic]:
    ws = load_workspace(root)
    ctx = AnalysisContext(config=config)
    diags: list[Diagnostic] = []
    for doc in ws.documents:
        if doc.parse_error is not None:
            diags.append(Diagnostic(
                rule="INT001", severity="info",
                message=f"문서를 파싱하지 못해 분석에서 제외했습니다: {doc.parse_error}",
                range=SourceRange(file=doc.path, start_line=1, start_col=1,
                                  end_line=1, end_col=1, start_offset=0, end_offset=0),
            ))
    analyzers = [ReferenceAnalyzer()]
    if terms_path is not None and terms_path.exists():
        analyzers.insert(0, TermAnalyzer(load_term_dictionary(terms_path)))
    for analyzer in analyzers:
        diags.extend(analyzer.analyze(ws, ctx))
    return diags
