from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.candidates import rank_candidates
from ttoryeot.config import default_config
from ttoryeot.diagnostics.models import Candidate, Diagnostic
from ttoryeot.ir.models import WorkspaceIR

DEFAULTS = default_config()["reference"]


def _self_evident_tie(unique: list, ref_head: str) -> bool:
    """1위와 점수가 정확히 같은 동점 집합에서 지시어 head와 일치하는 후보가 유일하면
    True — 독자가 head로 자명하게 해소하므로 발화하지 않는다.

    round-3 잔존 재판정의 '자명한 1위' 클래스(5/28건, 예: k8s의 '해당 파드'에
    '파드' 0.925 = '노드' 0.925 — 현행 가중치 기준 실측)가 근거다. 세 가지 좁힘이 전부 의도적이다:

    - **exact tie만**: 시드 벤치의 '해당 데이터'는 0.68 vs 0.51로 동점이 아니다 —
      근사 동점(gap<threshold)까지 확장하면 시드 recall이 죽는다. 확장은 라벨
      데이터가 생긴 뒤의 일이다.
    - **strict equality만**: 스코어러의 head_match 자질은 부분 문자열 포함
      (ref.head in phrase.text)도 인정하지만, 독자의 자명한 해소는 head 그 자체의
      일치를 요구한다.
    - **정확히 하나만**: 0개면 head가 아무 단서도 아니고, 2개 이상이면 head가
      아무것도 갈라주지 않는다('사용자 테이블' vs '주문 테이블') — 기존대로 발화.
    """
    tied = [c for c in unique if c.score == unique[0].score]
    if len(tied) < 2:
        return False
    return sum(1 for c in tied if c.phrase.head == ref_head) == 1


def _explain(top: list) -> str:
    """상위 후보의 자질별 원점수를 근거 문자열로 분해한다 (Gleich 외 2010 —
    왜 모호한지를 설명해 작성자를 교육한다)."""
    parts = []
    for c in top:
        feats = " ".join(f"{k}={v:g}" for k, v in c.features.items())
        parts.append(f"{c.phrase.text}({feats})")
    return "후보 점수 근거: " + " · ".join(parts)


class ReferenceAnalyzer:
    rule_ids = ("REF101",)

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        cfg = {**DEFAULTS, **(ctx.config.get("reference") or {})}
        # suppress_heads는 그룹 단위로도 부분 오버라이드를 허용한다 — 섹션 통째
        # 치환이면 CLI(--config 딥머지) 경로와 직접 주입 경로의 의미가 갈린다.
        groups = {**(DEFAULTS.get("suppress_heads") or {}),
                  **(cfg.get("suppress_heads") or {})}
        suppress: set[str] = set()
        for group in groups.values():
            suppress.update(group or [])
        for doc in ws.documents:
            # 문서 내 문장 시퀀스 (heading에서 윈도 리셋)
            window = []
            for block in doc.blocks:
                if block.kind == "heading":
                    window = []
                    continue
                for sent in block.sentences:
                    for ref in sent.references:
                        # 구조 참조('이 글'·'위 예시 앱')와 담화 지시('이 방법')는
                        # head 또는 지시어 바로 뒤 명사로 판별해 억제한다.
                        parts = ref.text.split()
                        if ref.head in suppress or (
                            len(parts) > 1 and parts[1] in suppress
                        ):
                            continue
                        ranked = rank_candidates(ref, window[-cfg["window"]:],
                                                 cfg["weights"])
                        # 같은 표면형의 반복 언급만 하나로 접는다 —
                        # '사용자 테이블'과 '주문 테이블'은 head가 같아도 서로 다른 후보
                        seen, unique = set(), []
                        for c in ranked:
                            if c.phrase.text not in seen:
                                seen.add(c.phrase.text)
                                unique.append(c)
                        if (
                            len(unique) >= 2
                            and unique[0].score >= cfg.get("min_top_score", 0.0)
                            and (unique[0].score - unique[1].score) < cfg["threshold"]
                        ):
                            # 발화 판정 직전의 동점 깨기 — 정확 동점이면서 head 일치
                            # 후보가 유일하면 침묵 (근거는 _self_evident_tie docstring)
                            if _self_evident_tie(unique, ref.head):
                                continue
                            yield Diagnostic(
                                rule="REF101", severity="warning",
                                message=f"'{ref.text}'의 지시 대상이 불명확합니다.",
                                range=ref.range,
                                candidates=[
                                    Candidate(text=c.phrase.text, score=c.score)
                                    for c in unique[:3]
                                ],
                                evidence=_explain(unique[:2]),
                            )
                    window.append(sent)
