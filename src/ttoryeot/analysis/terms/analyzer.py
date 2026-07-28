import re
from collections import defaultdict
from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.dictionary import TermEntry, TermOccurrence, build_symbol_table
from ttoryeot.diagnostics.models import Diagnostic
from ttoryeot.ir.models import WorkspaceIR


def _definition_pattern(surface: str) -> re.Pattern:
    esc = re.escape(surface)
    return re.compile(
        rf"{esc}(?:이란|란|은|는)\s+(.+?)(?:이다|입니다|를 말합니다|을 말합니다)"
    )


def _list_definition_pattern(surface: str) -> re.Pattern:
    """list_item의 `용어: 정의` 형식 (스펙 §6.2)."""
    esc = re.escape(surface)
    return re.compile(rf"^\s*{esc}\s*[:：]\s*(.+)$")


_TRAILING_COPULA = re.compile(r"(?:이다|입니다|를 말합니다|을 말합니다)?\.?\s*$")


def _normalize_definition(raw: str) -> str:
    """공백을 접고 꼬리의 서술 어미·마침표를 떼어, 프로즈형('…의 집합이다')과
    list_item형('…의 집합') 정의를 같은 내용이면 같은 문자열로 만든다.
    '사이다'처럼 어미와 표면이 겹치는 명사로 끝나는 정의는 과하게 잘리는 알려진 한계."""
    return _TRAILING_COPULA.sub("", " ".join(raw.split()), count=1)


class TermAnalyzer:
    rule_ids = ("TERM100", "TERM101", "TERM102")

    def __init__(self, entries: list[TermEntry]):
        self.entries = entries

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        table = build_symbol_table(ws, self.entries)
        for entry in self.entries:
            occs = table[entry.canonical]
            yield from self._mixed_usage(entry, occs)
            yield from self._conflicting_definitions(ws, entry)

    def _mixed_usage(
        self, entry: TermEntry, occs: list[TermOccurrence]
    ) -> Iterable[Diagnostic]:
        by_doc: dict[str, set[str]] = defaultdict(set)
        for o in occs:
            by_doc[o.doc_path].add(o.surface)
        all_surfaces = {o.surface for o in occs}
        docs_with_mixing = {
            doc_path for doc_path, surfaces in by_doc.items() if len(surfaces) > 1
        }
        # TERM100: 한 문서 안에 두 표기 — 혼용 문서마다 모두 보고한다 (한 문서에서
        # 멈추면 그 뒤 문서들의 TERM100/TERM101이 통째로 유실된다).
        for doc_path in docs_with_mixing:
            for o in occs:
                if o.doc_path == doc_path and o.surface != entry.canonical:
                    yield Diagnostic(
                        rule="TERM100", severity="warning",
                        message=f"'{o.surface}'와 '{entry.canonical}' 표기가 같은 문서에서 혼용됩니다.",
                        range=o.range,
                    )
        # TERM101: 문서 간 혼용 — 이미 TERM100으로 보고된 문서는 중복 보고하지 않는다.
        if len(all_surfaces) > 1:
            for o in occs:
                if o.surface != entry.canonical and o.doc_path not in docs_with_mixing:
                    yield Diagnostic(
                        rule="TERM101", severity="warning",
                        message=f"'{o.surface}'는 다른 문서의 '{entry.canonical}' 표기와 불일치합니다.",
                        range=o.range,
                    )

    def _conflicting_definitions(
        self, ws: WorkspaceIR, entry: TermEntry
    ) -> Iterable[Diagnostic]:
        prose = _definition_pattern(entry.canonical)
        listdef = _list_definition_pattern(entry.canonical)
        found: list[tuple[str, str, object]] = []  # (normalized_def, doc, range)
        for doc, block, sent in ws.iter_sentences():
            m = prose.search(sent.text)
            if m is None and block.kind == "list_item":
                m = listdef.match(sent.text)
            if m:
                found.append((_normalize_definition(m.group(1)), doc.path, sent.range))
        # glossary 파일의 정의를 정본으로 우선 — 충돌 진단은 나머지 정의 위치에 단다
        found.sort(key=lambda f: (0 if "glossary" in f[1] else 1, f[1]))
        definitions = {d for d, _, _ in found}
        if len(definitions) > 1:
            canonical_def = found[0][0]
            for defn, _doc, rng in found[1:]:
                if defn == canonical_def:
                    # 정본(glossary)과 동일한 정의는 충돌이 아니다 — 오탐 방지.
                    continue
                yield Diagnostic(
                    rule="TERM102", severity="warning",
                    message=f"'{entry.canonical}'의 정의가 다른 문서의 정의와 충돌합니다.",
                    range=rng,
                    evidence=f"기존 정의: {found[0][0]} ({found[0][1]})",
                )
