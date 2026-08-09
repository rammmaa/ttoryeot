import re
from collections import Counter, defaultdict
from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.dictionary import (
    TermEntry,
    TermOccurrence,
    build_symbol_table,
    position_in_sentence,
)
from ttoryeot.analysis.terms.variants import is_variant_candidate_pair, normalize
from ttoryeot.config import default_config
from ttoryeot.parsing.lowering import INLINE_CODE
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

# 어간 표면형을 얻기 위해 꼬리에서 떼는 태그. 구두점은 SL(로마자)·SN(숫자)·SH(한자)를
# 제외한 기호류만 포함한다 — 로마자·숫자는 표기의 일부일 수 있다.
_STRIPPABLE_SUFFIX_TAGS = {
    "XSV", "XSA", "XSN", "VCP", "VCN",
    "SF", "SP", "SS", "SE", "SO", "SW", "SSO", "SSC",
}


def _variant_candidates(sent) -> list[tuple[str, SourceRange]]:
    """표기 변이 후보 표면형을 두 경로로 모은다.

    (1) 명사구 — '데이터 세트'처럼 어절을 걸친 띄어쓰기 변이를 잡는다.
    (2) 조사를 뗀 어절 — 외래어 변이('오너십'/'오너쉽')는 **Kiwi가 오분석하는
        바로 그 단어**라서 명사구로 잡히지 않는다(오너+십, 오너+쉽/VA). 변이 탐지가
        분석기의 실패 지점을 대상으로 하므로, 분석에 덜 의존하는 표면형이 필요하다.
    """
    out = [(np.text, np.range) for np in sent.noun_phrases]
    base = sent.range.start_offset
    eojeol_start = 0
    text = sent.text
    # 인라인 코드 안의 표기는 후보가 아니다. 명사구 경로는 lowering에서 이미
    # 걸러지지만, 이 어절 경로는 원문에서 다시 긁으므로 여기서도 걸러야 한다.
    code_spans = [(m.start(), m.end()) for m in INLINE_CODE.finditer(text)]
    while eojeol_start < len(text):
        end = eojeol_start
        while end < len(text) and not text[end].isspace():
            end += 1
        if end > eojeol_start:
            inner = [
                t for t in sent.tokens
                if base + eojeol_start <= t.range.start_offset < base + end
            ]
            # 조사·어미·파생 접미사·구두점을 떼어 어간 표면형만 남긴다.
            # XSV/XSA/XSN을 떼면 '공유하'→'공유', '웹사이트들'→'웹사이트'가 되어
            # 활용·굴절형이 후보로 새지 않는다. 구두점 토큰(SF/SP/…)도 떼야 하는데,
            # 안 떼면 '제공하며,'의 쉼표가 그 앞 어미의 스트립을 막는다.
            # 반면 오분석된 외래어('오너쉽'의 쉽/VA-I)는 떼지 않아야 표면형이 보존된다.
            while inner and (inner[-1].tag[0] in ("J", "E")
                             or inner[-1].tag in _STRIPPABLE_SUFFIX_TAGS):
                inner.pop()
            # 용언 어절은 표기 변이 후보가 아니다 — 활용형끼리 자소가 가까워
            # ('만들어가/만들어본', '알려주/알려진') 노이즈의 큰 축이었다.
            # 첫 토큰으로 판정해야 오분석된 외래어('오너쉽' = 오너/NNG + 쉽/VA-I)가
            # 살아남는다.
            if inner and inner[0].tag[0] == "V":
                inner = []
            if inner:
                # 마스킹된 코드 스팬은 공백이 없어 Kiwi가 여러 어절을 한 토큰으로
                # 묶을 수 있다 — 어절 끝으로 잘라 후보가 어절을 넘지 않게 한다.
                stem_end = min(inner[-1].range.end_offset - base, end)
                raw = text[eojeol_start:stem_end]
                surface = raw.strip("\"'`.,·:;!?()[]{}<>")
                lead = len(raw) - len(raw.lstrip("\"'`.,·:;!?()[]{}<>"))
                s_off, e_off = eojeol_start + lead, eojeol_start + lead + len(surface)
                overlaps_code = any(
                    a < e_off and s_off < b for a, b in code_spans
                )
                if surface and not overlaps_code and any(
                    ch.isalnum() for ch in surface
                ):
                    sl, sc = position_in_sentence(
                        text, sent.range.start_line, sent.range.start_col, s_off)
                    el, ec = position_in_sentence(
                        text, sent.range.start_line, sent.range.start_col, e_off)
                    out.append((
                        surface,
                        SourceRange(
                            file=sent.range.file,
                            start_line=sl, start_col=sc,
                            end_line=el, end_col=ec,
                            start_offset=base + s_off,
                            end_offset=base + e_off,
                        ),
                    ))
        eojeol_start = end + 1
    return out


def _normalize_definition(raw: str) -> str:
    """공백을 접고 꼬리의 서술 어미·마침표를 떼어, 프로즈형('…의 집합이다')과
    list_item형('…의 집합') 정의를 같은 내용이면 같은 문자열로 만든다.
    '사이다'처럼 어미와 표면이 겹치는 명사로 끝나는 정의는 과하게 잘리는 알려진 한계."""
    return _TRAILING_COPULA.sub("", " ".join(raw.split()), count=1)


class TermAnalyzer:
    rule_ids = ("TERM100", "TERM101", "TERM102", "TERM103", "TERM104", "TERM105")

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
        if tcfg.get("suggest_variants"):
            yield from self._notation_variants(ws, tcfg)

    def _notation_variants(self, ws: WorkspaceIR, tcfg: dict) -> Iterable[Diagnostic]:
        """TERM105: 사전에 없는 표기 변이 후보를 자소 거리로 발견한다.

        TERM100/101은 사전에 적힌 표기만 볼 수 있어, 아직 등재되지 않은 혼용은
        원리적으로 탐지하지 못한다. 이 규칙이 그 공백을 메운다 (RedPen의 읽기 기반
        변이 그룹핑의 한국어 자소판). 제안이므로 info + opt-in.
        """
        max_ratio = float(tcfg.get("variant_max_ratio",
                                   _TERM_DEFAULTS["variant_max_ratio"]))
        min_count = int(tcfg.get("variant_min_count",
                                 _TERM_DEFAULTS["variant_min_count"]))
        min_syllables = int(tcfg.get("variant_min_syllables",
                                     _TERM_DEFAULTS["variant_min_syllables"]))
        max_distance = int(tcfg.get("variant_max_distance",
                                    _TERM_DEFAULTS["variant_max_distance"]))
        minority_ratio = float(tcfg.get("variant_minority_ratio",
                                        _TERM_DEFAULTS["variant_minority_ratio"]))
        minority_max_count = int(tcfg.get("variant_minority_max_count",
                                          _TERM_DEFAULTS["variant_minority_max_count"]))
        known = {s for e in self.entries for s, _status in e.surfaces()}

        counts: dict[str, int] = {}
        first: dict[str, SourceRange] = {}
        for _doc, _block, sent in ws.iter_sentences():
            for text, rng in _variant_candidates(sent):
                counts[text] = counts.get(text, 0) + 1
                first.setdefault(text, rng)

        # 같은 정규화 자소 길이대끼리만 비교해 O(n^2) 폭발을 막는다
        buckets: dict[tuple[str, int], list[str]] = {}
        for text, n in counts.items():
            if n < min_count:
                continue
            norm = normalize(text)
            if not norm:
                continue
            for length in (len(norm) - 1, len(norm), len(norm) + 1):
                buckets.setdefault((norm[0], length), []).append(text)

        reported: set[tuple[str, str]] = set()
        for group in buckets.values():
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    pair = tuple(sorted((a, b)))
                    if pair in reported or a == b:
                        continue
                    if a in known and b in known:
                        continue  # 사전에 있으면 TERM100/101 담당
                    if not is_variant_candidate_pair(
                        a, b, min_syllables=min_syllables,
                        max_distance=max_distance, max_ratio=max_ratio,
                    ):
                        continue
                    # 빈도 비대칭: 표기 변이는 소수 이형태이고, 대등한 빈도로 공존하면
                    # 서로 다른 어휘일 가능성이 높다('온라인'/'오프라인').
                    # 소수 표기가 절대적으로 드물거나(작은 문서 집합) 상대적으로
                    # 희소해야(큰 코퍼스) 후보로 인정한다.
                    na, nb = counts[a], counts[b]
                    minority = min(na, nb)
                    if (minority > minority_max_count
                            and minority / max(na, nb) > minority_ratio):
                        continue
                    reported.add(pair)
                    lo, hi = pair
                    # 띄어쓰기 변이(정규화 후 동일)와 철자 변이를 구분해 알린다 —
                    # 실측 정밀도가 크게 다르다(표본 30건: 띄어쓰기 6/6 vs 철자 ~20%).
                    kind = "띄어쓰기" if normalize(lo) == normalize(hi) else "철자"
                    yield Diagnostic(
                        rule="TERM105", severity="info",
                        message=(
                            f"{kind} 변이 후보입니다: '{lo}'({counts[lo]}회) / "
                            f"'{hi}'({counts[hi]}회) — 하나로 통일하고 용어 사전에 "
                            f"등록할지 검토하세요."
                        ),
                        range=first[lo] if first[lo].start_offset
                        <= first[hi].start_offset else first[hi],
                    )

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
        # 표면형별 워크스페이스 전역 빈도. 대칭 '불일치'는 어느 쪽을 고칠지 말해주지
        # 않는다 — LanguageTool의 일관성 규칙이 텍스트 전역 빈도로 최빈형을 정본
        # 삼듯 빈도를 증거로 싣는다. 다만 방향은 빈도가 아니라 **사전이 정한다**
        # (사전이 정책이다). 또렷은 저장소 스코프라 문서 하나보다 표본이 크다.
        counts = Counter(o.surface for o in occs)
        canonical_n = counts.get(entry.canonical, 0)
        # 정본 표기의 위치 — RedPen이 오류 메시지에 변이 출현 위치를 싣는 관행.
        # '어디를 참고해 고칠까'를 알려줘야 진단이 행동으로 이어진다. symbol table은
        # 긴 표면형 우선으로 매칭해 문장 안 순서가 등장 순이 아닐 수 있으므로
        # 문서·줄·칸으로 정렬해 결정적으로 만든다.
        # 빈도는 워크스페이스 전역값이므로 '같은 문서에서' 문장과 결합할 때
        # 스코프 표식('전체')을 붙인다 — 문서 내 빈도로 오독되는 것을 막는다.
        canonical_part = f"'{entry.canonical}'(전체 {canonical_n}회)"
        canonical_occs = sorted(
            (o for o in occs if o.surface == entry.canonical),
            key=lambda o: (o.doc_path, o.range.start_line, o.range.start_col),
        )

        def evidence(surface_n: int) -> str | None:
            parts: list[str] = []
            if canonical_occs:
                # 표시 단위가 file:line이므로 같은 키는 하나로 접는다 — 한 줄에
                # 여러 번 등장한 정본이 3칸 예산을 다 소모하면 안 된다.
                # 최대 3곳까지만 — evidence가 코퍼스 크기에 비례해 자라면 안 된다.
                locations = list(dict.fromkeys(
                    f"{o.doc_path}:{o.range.start_line}" for o in canonical_occs
                ))
                shown = " · ".join(locations[:3])
                if len(locations) > 3:
                    shown += f" 외 {len(locations) - 3}곳"
                parts.append(f"정본 '{entry.canonical}' 위치: {shown}")
            if 0 < canonical_n < surface_n:
                # canonical_n == 0이면 메시지가 이미 '코퍼스에 등장하지 않습니다'로
                # 분기하므로 '소수(0회)' 주의까지 겹치면 모순 문장이 된다.
                # 사전의 canonical이 전역 빈도상 소수인 경계 케이스 — 방향은 그대로
                # 사전을 따르되(위 정책), 사전 재검토를 유도하는 주의를 덧붙인다.
                parts.append(
                    f"주의: 정본 표기가 소수({canonical_n}회 vs {surface_n}회)입니다"
                )
            return " — ".join(parts) or None

        # TERM100: 한 문서 안에 두 표기 — 혼용 문서마다 모두 보고한다 (한 문서에서
        # 멈추면 그 뒤 문서들의 TERM100/TERM101이 통째로 유실된다).
        # set 순회는 PYTHONHASHSEED에 따라 순서가 흔들린다 — 진단 순서까지
        # 결정적이어야 한다는 주장(README)에 맞춰 정렬한다.
        for doc_path in sorted(docs_with_mixing):
            for o in occs:
                if o.doc_path == doc_path and o.surface != entry.canonical:
                    yield Diagnostic(
                        rule="TERM100", severity="warning",
                        message=(
                            f"'{o.surface}'(전체 {counts[o.surface]}회)와(과) "
                            + canonical_part
                            + " 표기가 같은 문서에서 혼용됩니다."
                            if canonical_n
                            else f"'{o.surface}'(전체 {counts[o.surface]}회) 표기가 "
                            f"같은 문서에서 혼용됩니다 — 사전 정본 "
                            f"'{entry.canonical}' 표기가 코퍼스에 등장하지 않습니다."
                        ),
                        range=o.range,
                        evidence=evidence(counts[o.surface]),
                    )
        # TERM101: 문서 간 혼용 — 이미 TERM100으로 보고된 문서는 중복 보고하지 않는다.
        if len(all_surfaces) > 1:
            for o in occs:
                if o.surface != entry.canonical and o.doc_path not in docs_with_mixing:
                    yield Diagnostic(
                        rule="TERM101", severity="warning",
                        message=(
                            f"'{o.surface}'(전체 {counts[o.surface]}회)은(는) "
                            f"다른 문서의 " + canonical_part + " 표기와 불일치합니다."
                            if canonical_n
                            else f"'{o.surface}'(전체 {counts[o.surface]}회)은(는) "
                            f"사전 정본과 불일치합니다 — 정본 '{entry.canonical}' "
                            f"표기가 코퍼스에 등장하지 않습니다."
                        ),
                        range=o.range,
                        evidence=evidence(counts[o.surface]),
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
