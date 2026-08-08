from pathlib import Path

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.chains import NounChainAnalyzer
from ttoryeot.parsing.workspace import load_workspace
from ttoryeot.runner import run_workspace

# probe 실측(과제 브리프): 이 문장에서 Kiwi lowering이 6어절 명사구
# '주문 데이터 파이프라인 배치 처리 설정'을 하나의 런으로 잡는다.
CHAIN = "주문 데이터 파이프라인 배치 처리 설정을 확인한다.\n"
ON = {"ambiguity": {"noun_chain": True}}


def make_ws(tmp_path: Path, content: str):
    (tmp_path / "doc.md").write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def run(ws, config=None):
    ctx = AnalysisContext(config=config or {})
    return list(NounChainAnalyzer().analyze(ws, ctx))


def test_off_by_default_is_silent(tmp_path):
    """기본 off — 발화율 실측 전에는 opt-in이다 (TERM103~105와 같은 정책)."""
    assert run(make_ws(tmp_path, CHAIN)) == []


def test_long_chain_fires_info_with_exact_range(tmp_path):
    ws = make_ws(tmp_path, CHAIN)
    diags = run(ws, ON)
    assert [d.rule for d in diags] == ["AMB101"]
    d = diags[0]
    assert d.severity == "info"
    # 오프셋 불변식: 진단 range의 원문 슬라이스가 정확히 그 명사구 텍스트다
    assert CHAIN[d.range.start_offset:d.range.end_offset] == (
        "주문 데이터 파이프라인 배치 처리 설정"
    )
    assert "6어절" in d.message


def test_chain_at_threshold_is_silent(tmp_path):
    """3어절은 상한 이내(STE 2.1: 3단어 '이하' 허용) — 경계값에서 침묵해야 한다."""
    ws = make_ws(tmp_path, "배치 처리 설정을 확인한다.\n")
    assert run(ws, ON) == []


def test_inline_code_chain_is_silent(tmp_path):
    """코드 스팬 안의 명사구는 lowering이 이미 제외하지만, 규칙의 침묵을 테스트로
    고정한다 — 코드 식별자 나열은 산문 모호성이 아니다."""
    ws = make_ws(tmp_path, "`주문 데이터 파이프라인 배치 처리 설정`을 확인한다.\n")
    assert run(ws, ON) == []


def test_max_eojeol_is_configurable(tmp_path):
    ws = make_ws(tmp_path, CHAIN)
    cfg = {"ambiguity": {"noun_chain": True, "max_noun_chain_eojeol": 6}}
    assert run(ws, cfg) == []


def test_pragma_suppression_via_runner(tmp_path):
    (tmp_path / "doc.md").write_text(
        "<!-- ttoryeot:disable AMB101 -->\n\n" + CHAIN, encoding="utf-8"
    )
    diags = run_workspace(tmp_path, None, ON)
    assert [d.rule for d in diags if d.rule == "AMB101"] == []
    # AMB101이 runner의 known_rules에 포함되어야 프라그마가 INT002 오보 없이 먹힌다
    assert [d.rule for d in diags if d.rule == "INT002"] == []


def test_runner_emits_amb101_when_enabled(tmp_path):
    (tmp_path / "doc.md").write_text(CHAIN, encoding="utf-8")
    diags = run_workspace(tmp_path, None, ON)
    assert [d.rule for d in diags] == ["AMB101"]


def test_latin_only_noun_runs_are_not_korean_noun_chains(tmp_path):
    """실측(fe-news 64%·react 71%)에서 발화의 최대 노이즈가 라틴 전용 SL 런
    (영어 제목·영어 문장)이었다 — 'A Visual Guide to React Rendering'은 한국어
    명사 나열 모호성이 아니다. 한글이 하나도 없는 명사구는 대상에서 제외한다."""
    # 실제 노이즈 클래스 그대로 — 뉴스레터에 섞인 영어 문장/제목 (fe-news 실측 64%)
    ws = make_ws(tmp_path, "A Visual Guide to React Rendering Behavior explains the process.\n")
    diags = run(ws, ON)
    assert all("Visual" not in d.message for d in diags)


def test_four_eojeol_chain_fires_at_default_threshold(tmp_path):
    """기본 상한 3의 경계 핀 — 4어절이 발화해야 한다. default.yaml의
    max_noun_chain_eojeol이 드리프트하면 이 테스트가 잡는다."""
    ws = make_ws(tmp_path, "주문 데이터 배치 설정을 확인한다.\n")
    diags = run(ws, ON)
    assert len(diags) == 1 and "4어절" in diags[0].message
