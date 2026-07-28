import re
from collections import defaultdict
from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.dictionary import TermEntry, TermOccurrence, build_symbol_table
from ttoryeot.config import default_config
from ttoryeot.diagnostics.models import Diagnostic
from ttoryeot.ir.models import WorkspaceIR
from ttoryeot.ir.source import SourceRange


def _definition_pattern(surface: str) -> re.Pattern:
    esc = re.escape(surface)
    return re.compile(
        rf"{esc}(?:이란|란|은|는)\s+(.+?)(?:이다|입니다|를 말합니다|을 말합니다)"
    )


def _list_definition_pattern(surface: str) -> re.Pattern:
    """list_item의 `용어: 정의` 형식 (스펙 §6.2). 정의가 하드랩으로 여러 줄에
    걸치면 탐지하지 못한다(문장 단위 매칭·`.`이 개행을 넘지 않음) — 조용한
    미탐일 뿐 오탐은 없다."""
    esc = re.escape(surface)
    return re.compile(rf"^\s*{esc}\s*[:：]\s*(.+)$")


_TRAILING_COPULA = re.compile(r"(?:이다|입니다|를 말합니다|을 말합니다)?\.?\s*$")

_TERM_DEFAULTS = default_config()["terms"]


def _normalize_definition(raw: str) -> str:
    """공백을 접고 꼬리의 서술 어미·마침표를 떼어, 프로즈형('…의 집합이다')과
    list_item형('…의 집합') 정의를 같은 내용이면 같은 문자열로 만든다.
    '사이다'처럼 어미와 표면이 겹치는 명사로 끝나는 정의는 과하게 잘리는 알려진 한계."""
    return _TRAILING_COPULA.sub("", " ".join(raw.split()), count=1)


class TermAnalyzer:
    rule_ids = ("TERM100", "TERM101", "TERM102", "TERM103", "TERM104")

    def __init__(self, entries: list[TermEntry]):
        self.entries = entries

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        table = build_symbol_table(ws, self.entries)
        tcfg = ctx.config.get("terms") or {}
        for entry in self.entries:
            occs = table[entry.canonical]
            yield from self._mixed_usage(entry, occs)
            yield from self._conflicting_definitions(ws, entry)
            if tcfg.get("enforce_canonical"):
                yield from self._nonpreferred_surface(entry, occs)
        if tcfg.get("suggest_unknown"):
            yield from self._unknown_terms(ws, tcfg)

    def _unknown_terms(
        self, ws: WorkspaceIR, tcfg: dict
    ) -> Iterable[Diagnostic]:
        """TERM103 (스펙 §6.2): 사전에 없는 조직 고유 용어 후보 — NNP/SL을 포함한
        명사구가 임계 이상 반복되면 사전 등록 후보로 제안한다. 일반 명사(NNG)만으로
        된 구는 잡음이 많아 v1에서는 후보로 보지 않는다. opt-in (사전 성장 루프)."""
        min_count = int(tcfg.get("unknown_min_count", _TERM_DEFAULTS["unknown_min_count"]))
        min_docs = int(tcfg.get("unknown_min_docs", _TERM_DEFAULTS["unknown_min_docs"]))
        known = {s for e in self.entries for s, _status in e.surfaces()}
        counts: dict[str, int] = {}
        docs: dict[str, set[str]] = {}
        first: dict[str, SourceRange] = {}
        for doc, _block, sent in ws.iter_sentences():
            for np in sent.noun_phrases:
                if np.text in known:
                    continue
                toks = [
                    t for t in sent.tokens
                    if np.range.start_offset <= t.range.start_offset < np.range.end_offset
                ]
                if not any(t.tag in ("NNP", "SL") for t in toks):
                    continue
                counts[np.text] = counts.get(np.text, 0) + 1
                docs.setdefault(np.text, set()).add(doc.path)
                first.setdefault(np.text, np.range)
        for text, n in counts.items():
            if n >= min_count and len(docs[text]) >= min_docs:
                yield Diagnostic(
                    rule="TERM103", severity="info",
                    message=(
                        f"사전에 없는 반복 용어 후보입니다: '{text}' "
                        f"({n}회, {len(docs[text])}개 문서) — 용어 사전 등록을 검토하세요."
                    ),
                    range=first[text],
                )

    def _nonpreferred_surface(
        self, entry: TermEntry, occs: list[TermOccurrence]
    ) -> Iterable[Diagnostic]:
        # TERM104: 사전이 정본을 정하면 혼용 여부와 무관하게 비권장 표기를 플래그
        # — 혼용 검출(TERM100/101)과 달리 고립 문서의 '오너쉽'류를 잡는다 (1차
        # 정량 실험에서 실증된 간극). 표기 정책 선택이므로 opt-in.
        # admitted(써도 되는 이표기)는 제외한다 — 상태 축은 dictionary.TermStatus 참조.
        for o in occs:
            if o.surface != entry.canonical and o.status == "deprecated":
                yield Diagnostic(
                    rule="TERM104", severity="warning",
                    message=f"'{o.surface}'은(는) 사전 비권장 표기입니다 — 권장: '{entry.canonical}'.",
                    range=o.range,
                )

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
                        message=f"'{o.surface}'와(과) '{entry.canonical}' 표기가 같은 문서에서 혼용됩니다.",
                        range=o.range,
                    )
        # TERM101: 문서 간 혼용 — 이미 TERM100으로 보고된 문서는 중복 보고하지 않는다.
        if len(all_surfaces) > 1:
            for o in occs:
                if o.surface != entry.canonical and o.doc_path not in docs_with_mixing:
                    yield Diagnostic(
                        rule="TERM101", severity="warning",
                        message=f"'{o.surface}'은(는) 다른 문서의 '{entry.canonical}' 표기와 불일치합니다.",
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
