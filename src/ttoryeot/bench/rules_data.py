# 치환 베이스라인의 정의: 조사표(2026-07-26)의 '일괄 치환 후보' 시트 그대로 —
# 감사자가 전역 치환 안전으로 판정한 목록만 쓴다. 이슈 목록의 나머지 항목은
# 감사자 스스로 문맥 의존으로 본 것이므로 (예: '상관 없이'는 붙이고 '편향없이'는
# 띄는 상반 사례) 여기에 규칙을 만들지 않는 것이 공정한 대조군이다.
# category는 해당 이슈의 벤치 버킷(benchmark/data/category-map.md)과 정렬.
SUBSTITUTIONS: dict[str, tuple[str, str]] = {
    # 조사표 도착 전 시드
    "리쿠르팅": ("리크루팅", "loanword_spelling"),
    "타입스트립트": ("타입스크립트", "typo_or_damage"),
    "데이타": ("데이터", "loanword_spelling"),
    # 일괄 치환 후보 시트 (검색어 → 권장 표기 첫 대안)
    "워크샵": ("워크숍", "loanword_spelling"),
    "런칭": ("론칭", "loanword_spelling"),
    "컨퍼런스": ("콘퍼런스", "loanword_spelling"),
    "컨텐츠": ("콘텐츠", "loanword_spelling"),
    "리플렛": ("리플릿", "loanword_spelling"),
    "구요": ("고요", "grammar_agreement"),
    "신규입사자": ("신규 입사자", "spacing"),
    "문화의날": ("문화의 날", "spacing"),
    "제 1회": ("제1회", "spacing"),
    "또다른": ("또 다른", "spacing"),
    "일한지": ("일한 지", "spacing"),
    "한번도": ("한 번도", "spacing"),
}

REGEX_RULES: list[tuple[str, str]] = [
    (r"[가-힣]+중입니다", "spacing"),      # '준비중입니다' — 명사+중 붙여쓰기
    (r"열려있", "spacing"),                # '열려있는' → '열려 있는'
]

DEMONSTRATIVES = ("해당", "이", "그", "위")
