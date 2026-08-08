from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.parsing.workspace import load_workspace


def make_ws(tmp_path: Path, content: str):
    (tmp_path / "doc.md").write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def run(ws, config=None):
    ctx = AnalysisContext(config=config or {})
    return list(ReferenceAnalyzer().analyze(ws, ctx))


def test_ref101_on_ambiguous_reference(tmp_path):
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    diags = run(ws)
    assert [d.rule for d in diags] == ["REF101"]
    assert len(diags[0].candidates) >= 2


def test_clear_single_candidate_is_silent(tmp_path):
    ws = make_ws(tmp_path, "조인 결과를 만듭니다.\n\n해당 결과를 저장합니다.\n")
    assert run(ws) == []


def test_no_reference_no_diagnostic(tmp_path):
    ws = make_ws(tmp_path, "조인 결과를 저장합니다.\n")
    assert run(ws) == []


def test_section_boundary_cuts_window(tmp_path):
    ws = make_ws(tmp_path,
        "주문 테이블을 만듭니다.\n\n# 다른 섹션\n\n"
        "사용자 로그를 수집합니다.\n\n해당 로그를 저장합니다.\n")
    diags = run(ws)
    # 섹션 이전의 '주문 테이블'은 후보가 아니므로 후보는 '사용자 로그' 계열뿐 → 침묵
    assert diags == []


AMBIENT = "사용자 테이블과 주문 테이블을 조인합니다.\n\n"


def test_structural_reference_heads_suppressed(tmp_path):
    """외부 코퍼스 실측(2026-07-28 리포트) 근거 — '이 글'류 구조 참조는 선행사가
    프로즈 명사구가 아니라 문서·링크·코드블록 자체라 REF101 대상이 아니다."""
    ws = make_ws(tmp_path, AMBIENT + "이 글에서는 조인 방법을 설명합니다.\n")
    assert run(ws) == []


def test_discourse_deixis_heads_suppressed(tmp_path):
    """'이 방법'류 담화 지시는 선행 명제를 가리킨다 — NP 후보 랭킹의 대상이 아니다."""
    ws = make_ws(tmp_path, AMBIENT + "이 방법은 빠릅니다.\n")
    assert run(ws) == []


def test_structural_word_after_demonstrative_suppressed(tmp_path):
    """'위 예시 앱'처럼 head가 아니라 지시어 바로 뒤 명사가 구조어인 경우도 억제
    (외부 측정 실측 사례)."""
    ws = make_ws(tmp_path, AMBIENT + "위 예시 앱을 실행합니다.\n")
    assert run(ws) == []


def test_suppression_configurable_off(tmp_path):
    ws = make_ws(tmp_path, AMBIENT + "이 글에서는 조인 방법을 설명합니다.\n")
    diags = run(ws, {"reference": {"suppress_heads": {"structural": [], "discourse": []}}})
    assert [d.rule for d in diags] == ["REF101"]


def test_partial_suppress_override_keeps_other_group(tmp_path):
    """suppress_heads를 부분만 오버라이드하면 나머지 그룹은 기본 목록을 유지해야
    한다 — CLI(--config 딥머지)와 직접 주입의 의미가 갈리면 스윕 코드가 헛돈다."""
    ws = make_ws(tmp_path, AMBIENT + "이 방법은 빠릅니다.\n")
    assert run(ws, {"reference": {"suppress_heads": {"structural": []}}}) == []


def test_suppressed_head_hides_genuine_ambiguity_known_limitation(tmp_path):
    """의도된 v1 한계의 핀 — 두 구체적 '방법'이 경쟁해도 head가 담화 목록에 있으면
    억제된다. round-3에서 same-head 후보 존재 시 억제 해제를 검토할 때 이 테스트를
    갱신하라 (튜닝 챕터 한계 절 참조)."""
    ws = make_ws(tmp_path, "조인 방법과 정렬 방법을 비교합니다.\n\n해당 방법을 사용합니다.\n")
    assert run(ws) == []
    diags = run(ws, {"reference": {"suppress_heads": {"structural": [], "discourse": []}}})
    assert [d.rule for d in diags] == ["REF101"]


def test_role_score_is_graded_by_case_particle():
    """Centering(SUBJECT > OBJECT > OTHER)과 Lappin & Leass(subject 80 / accusative 50 /
    oblique 40)의 다단계 문법역. 한국어는 조사로 역이 표면에 드러나 영어보다 싸게
    구현된다 — 기존 1.0/0.3 이진에서 승격."""
    from ttoryeot.analysis.references.candidates import ROLE_SCORES

    assert ROLE_SCORES["topic"] > ROLE_SCORES["subject"] > ROLE_SCORES["object"]
    assert ROLE_SCORES["object"] > ROLE_SCORES["oblique"] > ROLE_SCORES["none"]


def test_topic_particle_outranks_nominative():
    """한국어 고유 신호 — 주제 표지 은/는(JX)은 주격 이/가(JKS)와 다른 형태소이고,
    담화 현저성이 더 높다. 영어 Centering이 주제를 '추론'해야 하는 것과 달리 한국어는
    표면에 찍혀 있다 (일본어 centering의 TOPIC > SUBJECT 위계와 같은 계열).
    이 둘을 뭉치면 한국어가 공짜로 주는 신호를 버리는 셈이다."""
    from ttoryeot.analysis.references.candidates import _role_score
    from ttoryeot.parsing.lowering import lower_document
    from ttoryeot.parsing.workspace import get_kiwi

    def role_of(text: str) -> float:
        doc = lower_document("a.md", text + "\n", get_kiwi())
        sent = doc.blocks[0].sentences[0]
        return _role_score(sent.noun_phrases[0], sent)

    assert role_of("주문 테이블은 크다.") > role_of("주문 테이블이 크다.")
    assert role_of("주문 테이블이 크다.") > role_of("주문 테이블을 만든다.")


def test_subject_candidate_outranks_object_candidate(tmp_path):
    ws = make_ws(tmp_path,
        "사용자 테이블이 주문 테이블을 참조합니다.\n\n해당 테이블을 조회합니다.\n")
    diags = run(ws, {"reference": {"threshold": 1.0}})  # 항상 발화시켜 순위를 본다
    assert diags and [c.text for c in diags[0].candidates][0] == "사용자 테이블"


def test_min_top_score_suppresses_weak_candidate_sets(tmp_path):
    """Ezzini et al.(ICSE 2022)의 θ_α — 격차만 보면 후보가 전부 약할 때도 침묵한다.
    1위 점수 자체가 낮으면 근거가 빈약하므로 발화하지 않는다."""
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    assert [d.rule for d in run(ws)] == ["REF101"]
    assert run(ws, {"reference": {"min_top_score": 0.99}}) == []


def test_diagnostic_explains_which_features_closed_the_gap(tmp_path):
    """Gleich et al.(REFSQ 2010)의 요구조건 — 왜 모호한지를 설명해 작성자를 교육한다.
    결정론적 가중합이라 자질 기여 분해가 자명한 것이 ML 대비 실질 우위다."""
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    diags = run(ws)
    assert diags[0].evidence is not None
    # 상위 두 후보의 자질별 점수가 근거에 드러나야 한다
    for feature in ("distance", "role", "head_match", "recency"):
        assert feature in diags[0].evidence


def test_threshold_configurable(tmp_path):
    ws = make_ws(tmp_path,
        "사용자 테이블과 주문 테이블을 조인합니다.\n\n해당 데이터를 저장합니다.\n")
    # 임계값 0이면 어떤 점수 차든 통과 → 진단 없음
    assert run(ws, {"reference": {"threshold": 0.0}}) == []


# ── 정확 동점의 head 일치 자명성 (round-3 잔존 클래스 5/28) ──────────────────
#
# 실제 문장으로 정확 동점을 만드는 것은 Kiwi의 문맥 의존 분해 때문에 취약하다.
# 동점 판정은 순수 함수(_self_evident_tie)를 ScoredCandidate 직접 구성으로 검증하고,
# 분석기 배선은 손으로 만든 IR(결정론적 점수)로 확인한다.

def _span(start: int, end: int):
    from ttoryeot.ir.source import SourceRange

    return SourceRange(file="doc.md", start_line=1, start_col=start + 1,
                       end_line=1, end_col=end + 1,
                       start_offset=start, end_offset=end)


def _cand(text: str, head: str, score: float, start: int = 0):
    from ttoryeot.analysis.references.candidates import ScoredCandidate
    from ttoryeot.ir.models import NounPhrase

    return ScoredCandidate(
        phrase=NounPhrase(text=text, head=head, range=_span(start, start + len(text))),
        score=score,
    )


def test_exact_tie_with_unique_head_match_is_self_evident():
    """k8s 실측 사례 — '해당 파드'에 후보 '파드' 0.90 = '노드' 0.90 정확 동점.
    동점 집합에서 head가 일치하는 후보가 유일하면 독자에겐 자명하다 (round-3
    잔존 재판정의 '자명한 1위' 클래스)."""
    from ttoryeot.analysis.references.analyzer import _self_evident_tie

    unique = [_cand("파드", "파드", 0.90), _cand("노드", "노드", 0.90, start=10)]
    assert _self_evident_tie(unique, "파드") is True


def test_exact_tie_with_two_head_matches_is_not_self_evident():
    """'사용자 테이블' vs '주문 테이블'에 '해당 테이블' — 동점이고 head도 둘 다
    일치하면 head가 아무것도 갈라주지 않는다 → 여전히 발화."""
    from ttoryeot.analysis.references.analyzer import _self_evident_tie

    unique = [_cand("사용자 테이블", "테이블", 0.90),
              _cand("주문 테이블", "테이블", 0.90, start=10)]
    assert _self_evident_tie(unique, "테이블") is False


def test_exact_tie_without_head_match_is_not_self_evident():
    from ttoryeot.analysis.references.analyzer import _self_evident_tie

    unique = [_cand("노드", "노드", 0.90), _cand("볼륨", "볼륨", 0.90, start=10)]
    assert _self_evident_tie(unique, "파드") is False


def test_near_tie_is_never_self_evident():
    """설계의 핵심 제약 — 시드 벤치의 '해당 데이터'는 0.68 vs 0.51로 동점이 아니다.
    근사 동점(gap<threshold)까지 확장하면 시드 recall이 죽는다. exact tie에만 적용."""
    from ttoryeot.analysis.references.analyzer import _self_evident_tie

    unique = [_cand("데이터", "데이터", 0.68), _cand("테이블", "테이블", 0.51, start=10)]
    assert _self_evident_tie(unique, "데이터") is False


def test_head_match_below_tie_set_does_not_count():
    """동점 집합은 1위와 점수가 '정확히 같은' 후보만이다 — 그 아래 순위의 head 일치는
    동점을 깨는 근거가 아니다."""
    from ttoryeot.analysis.references.analyzer import _self_evident_tie

    unique = [_cand("노드", "노드", 0.90), _cand("볼륨", "볼륨", 0.90, start=10),
              _cand("파드", "파드", 0.85, start=20)]
    assert _self_evident_tie(unique, "파드") is False


def test_tie_break_uses_strict_head_equality():
    """스코어러의 head_match는 부분 문자열 포함(ref.head in phrase.text)도 인정하지만,
    동점 깨기는 strict equality만 쓴다 — '파드 노드'(head=노드)는 텍스트에 '파드'가
    있어도 head 일치가 아니므로, 일치는 '파드' 하나뿐 → 자명."""
    from ttoryeot.analysis.references.analyzer import _self_evident_tie

    unique = [_cand("파드", "파드", 0.895), _cand("파드 노드", "노드", 0.895, start=10)]
    assert _self_evident_tie(unique, "파드") is True


def _tie_workspace(np_specs: list[tuple[str, str]], ref_head: str):
    """손으로 만든 IR — 후보 전부 같은 문장(같은 distance·recency), 토큰 없음(같은
    role)이라 head_match 자질까지 같으면 점수가 결정론적으로 정확 동점이 된다."""
    from ttoryeot.ir.models import (Block, DocumentIR, NounPhrase,
                                    ReferenceExpression, SentenceIR, WorkspaceIR)

    phrases, cursor = [], 0
    for text, head in np_specs:
        phrases.append(NounPhrase(text=text, head=head,
                                  range=_span(cursor, cursor + len(text))))
        cursor += len(text) + 2
    sent1 = SentenceIR(text="선행 문장", range=_span(0, cursor), noun_phrases=phrases)
    ref_text = f"해당 {ref_head}"
    ref = ReferenceExpression(text=ref_text, demonstrative="해당", head=ref_head,
                              range=_span(cursor + 1, cursor + 1 + len(ref_text)))
    sent2 = SentenceIR(text=ref_text, range=_span(cursor + 1, cursor + 10),
                       references=[ref])
    block = Block(kind="paragraph", range=_span(0, cursor + 10),
                  sentences=[sent1, sent2])
    doc = DocumentIR(path="doc.md", content_hash="x", blocks=[block])
    return WorkspaceIR(root=".", documents=[doc])


def test_analyzer_silences_exact_tie_with_unique_head_match():
    """배선 확인 — 발화 판정 직전에 동점 자명성 검사가 실제로 개입해야 한다."""
    ws = _tie_workspace([("파드", "파드"), ("파드 노드", "노드")], "파드")
    assert run(ws) == []


def test_analyzer_still_flags_tie_with_two_head_matches():
    """동점 + head 일치 2개면 기존대로 발화하고, candidates·evidence 분해도
    동점 상황에서 일관되게 남아야 한다."""
    ws = _tie_workspace([("사용자 테이블", "테이블"), ("주문 테이블", "테이블")], "테이블")
    diags = run(ws)
    assert [d.rule for d in diags] == ["REF101"]
    assert [c.text for c in diags[0].candidates] == ["사용자 테이블", "주문 테이블"]
    assert diags[0].candidates[0].score == diags[0].candidates[1].score
    for feature in ("distance", "role", "head_match", "recency"):
        assert feature in diags[0].evidence
