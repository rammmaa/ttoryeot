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

    assert ROLE_SCORES["subject"] > ROLE_SCORES["object"] > ROLE_SCORES["oblique"]
    assert ROLE_SCORES["oblique"] > ROLE_SCORES["none"]


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
