from pydantic import BaseModel

from ttoryeot.ir.models import NounPhrase, ReferenceExpression, SentenceIR

DEFAULT_WEIGHTS = {"distance": 0.4, "role": 0.25, "head_match": 0.25, "recency": 0.1}
SUBJ_OBJ_PARTICLES = {"이", "가", "을", "를", "은", "는"}


class ScoredCandidate(BaseModel):
    phrase: NounPhrase
    score: float


def _role_score(phrase: NounPhrase, sent: SentenceIR) -> float:
    for i, tok in enumerate(sent.tokens):
        if tok.range.end_offset == phrase.range.end_offset:
            nxt = sent.tokens[i + 1] if i + 1 < len(sent.tokens) else None
            if nxt is not None and nxt.tag.startswith("J") and nxt.form in SUBJ_OBJ_PARTICLES:
                return 1.0
    return 0.3


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
            score = (w["distance"] * distance + w["role"] * role
                     + w["head_match"] * head_match + w["recency"] * recency)
            scored.append(ScoredCandidate(phrase=phrase, score=round(score, 4)))
    scored.sort(key=lambda c: -c.score)
    return scored
