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
    if terms_path is not None:
        # 없는 파일을 조용히 건너뛰지 않는다 — load가 던지는 에러가 정직하다.
        # (CLI는 사전에 존재를 검사해 친절한 메시지 + exit 2로 처리한다.)
        analyzers.insert(0, TermAnalyzer(load_term_dictionary(terms_path)))
    known_rules = {r for a in analyzers for r in a.rule_ids}
    for analyzer in analyzers:
        diags.extend(analyzer.analyze(ws, ctx))
    diags.extend(_unknown_pragma_rules(ws, known_rules))
    return _apply_suppressions(ws, diags)


def _unknown_pragma_rules(ws, known_rules: set[str]) -> list[Diagnostic]:
    """프라그마에 적힌 규칙 이름이 실재하지 않으면 알린다 — 오타(대소문자 포함)가
    조용한 no-op이 되면 사용자는 억제가 걸린 줄로 착각한다."""
    out = []
    for doc in ws.documents:
        for s in doc.suppressions:
            for rule in s.rules:
                if rule in known_rules:
                    continue
                out.append(Diagnostic(
                    rule="INT002", severity="info",
                    message=(
                        f"억제 지시의 규칙 이름을 알 수 없습니다: '{rule}' — "
                        f"사용 가능: {', '.join(sorted(known_rules))}"
                    ),
                    range=SourceRange(
                        file=doc.path, start_line=s.line, start_col=1,
                        end_line=s.line, end_col=1,
                        start_offset=0, end_offset=0,
                    ),
                ))
    return out


def _apply_suppressions(ws, diags: list[Diagnostic]) -> list[Diagnostic]:
    by_path = {doc.path: doc for doc in ws.documents}

    def suppressed(diag: Diagnostic) -> bool:
        doc = by_path.get(diag.range.file)
        for s in (doc.suppressions if doc else []):
            if s.rules and diag.rule not in s.rules:
                continue
            if s.scope == "file":
                return True
            if s.scope == "next_line" and diag.range.start_line == s.line + 1:
                return True
        return False

    return [d for d in diags if not suppressed(d)]
