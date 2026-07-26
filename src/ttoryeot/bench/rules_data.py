# 조사표 기반 시드 규칙. 실제 조사표 도착 시 이 파일을 확장한다.
SUBSTITUTIONS: dict[str, tuple[str, str]] = {
    "리쿠르팅": ("리크루팅", "loanword_spelling"),
    "타입스트립트": ("타입스크립트", "loanword_spelling"),
    "데이타": ("데이터", "loanword_spelling"),
}

REGEX_RULES: list[tuple[str, str]] = [
    (r"[가-힣]+중입니다", "spacing"),      # '준비중입니다' — 명사+중 붙여쓰기
    (r"열려있", "spacing"),                # '열려있는' → '열려 있는'
]

DEMONSTRATIVES = ("해당", "이", "그", "위")
