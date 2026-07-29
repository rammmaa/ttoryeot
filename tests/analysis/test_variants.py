import pytest

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import TermEntry
from ttoryeot.analysis.terms.variants import jamo, jamo_distance_ratio
from ttoryeot.parsing.workspace import load_workspace

ON = AnalysisContext(config={"terms": {"suggest_variants": True}})


def make_ws(tmp_path, files):
    for name, content in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return load_workspace(tmp_path)


def test_jamo_decomposes_syllables():
    assert jamo("한") == "ㅎㅏㄴ"
    assert jamo("가") == "ㄱㅏ"  # 받침 없음
    assert jamo("API") == "API"  # 비한글은 그대로


@pytest.mark.parametrize("a,b", [
    ("오너십", "오너쉽"), ("메시지", "메세지"), ("컨텐츠", "콘텐츠"),
    ("워크샵", "워크숍"), ("애플리케이션", "어플리케이션"), ("레퍼런스", "래퍼런스"),
])
def test_real_variant_pairs_are_close(a, b):
    assert jamo_distance_ratio(a, b) <= 0.25


@pytest.mark.parametrize("a,b", [
    ("사용자", "개발자"), ("주문", "반품"), ("테이블", "데이터"), ("서버", "서비스"),
])
def test_distinct_terms_are_far(a, b):
    assert jamo_distance_ratio(a, b) > 0.25


def test_spacing_variation_is_zero_distance():
    assert jamo_distance_ratio("데이터 세트", "데이터세트") == 0.0


def test_term105_off_by_default(tmp_path):
    ws = make_ws(tmp_path, {
        # 실제 표기 변이는 비대칭이다 — 다수 표기 + 소수 이형태
        "a.md": ("오너십이 중요합니다. 오너십을 가집시다. 오너십을 강조합니다.\n"
                 "오너십이 있습니다. 오너십을 기릅니다. 오너십이 핵심입니다.\n"
                 "오너십을 봅니다. 오너십이 필요합니다. 오너십을 논합니다.\n"
                 "오너십이 자랍니다. 오너십을 키웁니다. 오너십이 중요합니다.\n"),
        "b.md": "오너쉽이 강한 팀입니다. 오너쉽을 봅니다.\n",
    })
    assert list(TermAnalyzer([]).analyze(ws, AnalysisContext())) == []


def test_term105_finds_variant_without_dictionary(tmp_path):
    """사전에 아무것도 적지 않아도 표기 변이를 발견해야 한다 — TERM100/101이
    사전 선언에 의존하는 구조적 공백을 메운다 (RedPen의 읽기 기반 변이 그룹핑의
    한국어 자소판)."""
    ws = make_ws(tmp_path, {
        # 실제 표기 변이는 비대칭이다 — 다수 표기 + 소수 이형태
        "a.md": ("오너십이 중요합니다. 오너십을 가집시다. 오너십을 강조합니다.\n"
                 "오너십이 있습니다. 오너십을 기릅니다. 오너십이 핵심입니다.\n"
                 "오너십을 봅니다. 오너십이 필요합니다. 오너십을 논합니다.\n"
                 "오너십이 자랍니다. 오너십을 키웁니다. 오너십이 중요합니다.\n"),
        "b.md": "오너쉽이 강한 팀입니다. 오너쉽을 봅니다.\n",
    })
    diags = [d for d in TermAnalyzer([]).analyze(ws, ON) if d.rule == "TERM105"]
    assert len(diags) == 1
    assert "오너십" in diags[0].message and "오너쉽" in diags[0].message
    assert "철자" in diags[0].message
    assert diags[0].severity == "info"


@pytest.mark.parametrize("a,b", [
    ("가지", "가치"), ("대안", "대한"), ("인식", "일식"), ("지속", "지식"),
])
def test_short_sino_korean_pairs_are_excluded(a, b):
    """2음절 한자어는 자소 1개 차이가 전혀 다른 단어다 — 실제 코퍼스 노이즈의
    최대 원인이었다. 음절 하한으로 거른다."""
    from ttoryeot.analysis.terms.variants import is_variant_candidate_pair

    assert not is_variant_candidate_pair(a, b)


@pytest.mark.parametrize("a,b", [
    ("오너십", "오너쉽"), ("메시지", "메세지"), ("컨텐츠", "콘텐츠"),
    ("워크샵", "워크숍"), ("리쿠르팅", "리크루팅"), ("데이터 세트", "데이터세트"),
])
def test_loanword_variants_survive_filters(a, b):
    from ttoryeot.analysis.terms.variants import is_variant_candidate_pair

    assert is_variant_candidate_pair(a, b)


def test_long_but_distant_pairs_are_excluded():
    """'엔지니어들'/'엔지니어링'은 비율로는 통과하지만 자소 3개가 달라 변이가 아니다."""
    from ttoryeot.analysis.terms.variants import is_variant_candidate_pair

    assert not is_variant_candidate_pair("엔지니어들", "엔지니어링")


def test_conjugated_stems_are_not_candidates(tmp_path):
    """용언 활용형('공유하'/'공유한')이 후보로 새면 안 된다 — 파생 접미사까지 뗀다."""
    ws = make_ws(tmp_path, {
        "a.md": "결과를 공유하고 공유한 뒤 공유할 것입니다.\n",
        "b.md": "내용을 공유했고 공유하며 공유하자.\n",
    })
    assert [d for d in TermAnalyzer([]).analyze(ws, ON) if d.rule == "TERM105"] == []


def test_balanced_frequency_pairs_are_excluded(tmp_path):
    """빈도가 대등하면 표기 변이가 아니라 서로 다른 어휘일 가능성이 높다
    ('온라인'/'오프라인', '사이드'/'사이트'). 표기 변이는 소수 이형태다."""
    body = "".join(
        f"오프라인 행사와 온라인 행사를 봅니다.\n\n" for _ in range(5)
    )
    ws = make_ws(tmp_path, {"a.md": body})
    pairs = [
        d.message for d in TermAnalyzer([]).analyze(ws, ON) if d.rule == "TERM105"
    ]
    assert not any("오프라인" in m and "온라인" in m for m in pairs)


def test_candidates_inside_inline_code_are_excluded(tmp_path):
    """인라인 코드 안의 표기는 후보가 아니다 — 명사구 경로는 이미 걸러지는데
    어절 경로가 원문에서 다시 긁어와 코드 속 용어로 진단이 나던 결함."""
    ws = make_ws(tmp_path, {
        "a.md": "설정은 `데이터세트` 입니다. 값은 `데이터세트` 입니다.\n",
        "b.md": "우리는 데이터 세트를 씁니다. 데이터 세트를 봅니다.\n",
    })
    assert [d for d in TermAnalyzer([]).analyze(ws, ON) if d.rule == "TERM105"] == []


def test_candidate_range_covers_the_named_surface(tmp_path):
    """진단 범위가 실제로 그 표면형을 덮어야 한다 — 종전엔 col=1 고정에 앞뒤
    구두점까지 포함된 범위였다."""
    ws = make_ws(tmp_path, {
        "a.md": ("오픈소스를 씁니다. 오픈소스를 만듭니다. 오픈소스를 봅니다.\n"
                 "오픈소스를 논합니다. 오픈소스가 좋습니다.\n"),
        "b.md": "우리는 오픈 소스를 씁니다. 오픈 소스를 좋아합니다.\n",
    })
    diags = [d for d in TermAnalyzer([]).analyze(ws, ON) if d.rule == "TERM105"]
    assert len(diags) == 1
    d = diags[0]
    source = (tmp_path / d.range.file).read_text(encoding="utf-8")
    assert source[d.range.start_offset:d.range.end_offset] in ("오픈소스", "오픈 소스")
    assert d.range.start_col > 0


def test_term105_ignores_distinct_terms(tmp_path):
    ws = make_ws(tmp_path, {
        "a.md": "사용자가 접속합니다. 사용자를 봅니다.\n",
        "b.md": "개발자가 배포합니다. 개발자를 봅니다.\n",
    })
    assert [d for d in TermAnalyzer([]).analyze(ws, ON) if d.rule == "TERM105"] == []


def test_term105_skips_pairs_already_in_dictionary(tmp_path):
    """사전에 이미 등재된 쌍은 TERM100/101이 담당하므로 중복 제안하지 않는다."""
    ws = make_ws(tmp_path, {
        # 실제 표기 변이는 비대칭이다 — 다수 표기 + 소수 이형태
        "a.md": ("오너십이 중요합니다. 오너십을 가집시다. 오너십을 강조합니다.\n"
                 "오너십이 있습니다. 오너십을 기릅니다. 오너십이 핵심입니다.\n"
                 "오너십을 봅니다. 오너십이 필요합니다. 오너십을 논합니다.\n"
                 "오너십이 자랍니다. 오너십을 키웁니다. 오너십이 중요합니다.\n"),
        "b.md": "오너쉽이 강한 팀입니다. 오너쉽을 봅니다.\n",
    })
    entries = [TermEntry(canonical="오너십", aliases=["오너쉽"])]
    diags = [d for d in TermAnalyzer(entries).analyze(ws, ON) if d.rule == "TERM105"]
    assert diags == []
