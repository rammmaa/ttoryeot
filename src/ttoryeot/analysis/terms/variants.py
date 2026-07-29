"""사전 없이 한국어 표기 변이를 발견하는 보조 모듈 (TERM105).

RedPen의 `JapaneseExpressionVariationValidator`가 일본어에서 읽기(yomi) 정규화로
하는 일을 한국어 자소(jamo) 분해로 한다. 한국어 표기 변이는 두 층에서 생긴다:

- **띄어쓰기 변이** — '데이터 세트' / '데이터세트' (공백 제거로 동일해짐)
- **외래어 표기 변이** — '오너십' / '오너쉽', '메시지' / '메세지' (자소 1~2개 차이)

실측(2026-07-29): 실제 변이쌍의 자소 편집거리 비율은 0.00~0.22, 서로 다른 용어는
0.50~0.83으로 갈린다. 기본 임계 0.25는 그 사이에 있다.
"""

_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_JONG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
_HANGUL_BASE = 0xAC00
_HANGUL_COUNT = 11172


def jamo(text: str) -> str:
    """한글 음절을 초·중·종성으로 분해한다 (종성 없으면 생략, 비한글은 그대로)."""
    out: list[str] = []
    for ch in text:
        code = ord(ch) - _HANGUL_BASE
        if 0 <= code < _HANGUL_COUNT:
            out.append(_CHO[code // 588])
            out.append(_JUNG[(code % 588) // 28])
            jong = _JONG[code % 28]
            if jong != " ":
                out.append(jong)
        else:
            out.append(ch)
    return "".join(out)


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def normalize(surface: str) -> str:
    """공백을 제거하고 자소로 분해한다 — 띄어쓰기 변이는 여기서 이미 동일해진다."""
    return jamo("".join(surface.split()))


def jamo_distance_ratio(a: str, b: str) -> float:
    """정규화 자소열의 편집거리를 긴 쪽 길이로 나눈 값 (0=동일)."""
    ja, jb = normalize(a), normalize(b)
    if not ja and not jb:
        return 0.0
    return _levenshtein(ja, jb) / max(len(ja), len(jb))


def syllable_count(text: str) -> int:
    return sum(
        1 for ch in text if 0 <= ord(ch) - _HANGUL_BASE < _HANGUL_COUNT
    )


# 기본 임계. 음절 하한이 실전 노이즈의 최대 원인을 잡는다 — 2음절 한자어는 자소
# 1개만 달라도 전혀 다른 단어다('가지/가치', '대안/대한', '인식/일식'). 반면 표기
# 변이는 외래어에 몰려 있어 대체로 3음절 이상이다('오너십', '메시지', '컨텐츠').
# 절대 거리 상한은 비율만으로는 긴 단어에서 새는 경우를 막는다('엔지니어들/엔지니어링').
MIN_SYLLABLES = 3
MAX_DISTANCE = 2
MAX_RATIO = 0.25


def is_variant_candidate_pair(
    a: str,
    b: str,
    *,
    min_syllables: int = MIN_SYLLABLES,
    max_distance: int = MAX_DISTANCE,
    max_ratio: float = MAX_RATIO,
) -> bool:
    if a == b:
        return False
    if min(syllable_count(a), syllable_count(b)) < min_syllables:
        return False
    ja, jb = normalize(a), normalize(b)
    if not ja or not jb:
        return False
    distance = _levenshtein(ja, jb)
    if distance > max_distance:
        return False
    return distance / max(len(ja), len(jb)) <= max_ratio
