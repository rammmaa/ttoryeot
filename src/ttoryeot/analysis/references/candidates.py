from pydantic import BaseModel

from ttoryeot.config import default_config
from ttoryeot.ir.models import NounPhrase, ReferenceExpression, SentenceIR

DEFAULT_WEIGHTS = default_config()["reference"]["weights"]

# 문법역 다단계 점수. Centering Theory(Grosz·Joshi·Weinstein 1995)의
# SUBJECT > OBJECT(S) > OTHER 위계와 Lappin & Leass(1994) RAP의 salience 가중치
# (subject 80 / accusative 50 / oblique 40)를 한국어 격조사에 대응시킨 것 —
# 한국어는 역이 조사로 표면화되어 영어보다 싸게 판별된다.
ROLE_SCORES = {"subject": 1.0, "object": 0.7, "oblique": 0.5, "none": 0.3}
SUBJECT_PARTICLES = {"이", "가", "은", "는", "께서"}
OBJECT_PARTICLES = {"을", "를"}


class ScoredCandidate(BaseModel):
    phrase: NounPhrase
    score: float
    # 자질별 원점수 (가중 전) — 진단 근거 분해용. 결정론적 가중합이라 분해가 자명하다.
    features: dict[str, float] = {}


def _role_score(phrase: NounPhrase, sent: SentenceIR) -> float:
    for i, tok in enumerate(sent.tokens):
        if tok.range.end_offset == phrase.range.end_offset:
            nxt = sent.tokens[i + 1] if i + 1 < len(sent.tokens) else None
            if nxt is None or not nxt.tag.startswith("J"):
                return ROLE_SCORES["none"]
            if nxt.form in SUBJECT_PARTICLES:
                return ROLE_SCORES["subject"]
            if nxt.form in OBJECT_PARTICLES:
                return ROLE_SCORES["object"]
            return ROLE_SCORES["oblique"]  # 부사격·관형격 등 나머지 조사
    return ROLE_SCORES["none"]


def rank_candidates(
    ref: ReferenceExpression,
    window: list[SentenceIR],
    weights: dict[str, float] | None = None,
) -> list[ScoredCandidate]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    scored = []
    n = len(window)
    for dist_idx, sent in enumerate(reversed(window)):  # dist_idx=0이 직전 문장
        for phrase in sent.noun_phrases:
            if phrase.range.end_offset >= ref.range.start_offset:
                continue  # 지시어 이후 등장 후보 제외
            distance = 1.0 / (1.0 + dist_idx)
            role = _role_score(phrase, sent)
            head_match = 1.0 if (ref.head == phrase.head or ref.head in phrase.text) else 0.0
            recency = 1.0 if dist_idx == 0 else 0.0
            features = {"distance": distance, "role": role,
                        "head_match": head_match, "recency": recency}
            score = sum(w[k] * v for k, v in features.items())
            scored.append(ScoredCandidate(
                phrase=phrase, score=round(score, 4),
                features={k: round(v, 4) for k, v in features.items()},
            ))
    scored.sort(key=lambda c: -c.score)
    return scored
