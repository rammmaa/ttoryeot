from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.candidates import rank_candidates
from ttoryeot.config import default_config
from ttoryeot.diagnostics.models import Candidate, Diagnostic
from ttoryeot.ir.models import WorkspaceIR

DEFAULTS = default_config()["reference"]


class ReferenceAnalyzer:
    rule_ids = ("REF101",)

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        cfg = {**DEFAULTS, **ctx.config.get("reference", {})}
        for doc in ws.documents:
            # 문서 내 문장 시퀀스 (heading에서 윈도 리셋)
            window = []
            for block in doc.blocks:
                if block.kind == "heading":
                    window = []
                    continue
                for sent in block.sentences:
                    for ref in sent.references:
                        ranked = rank_candidates(ref, window[-cfg["window"]:],
                                                 cfg["weights"])
                        # 같은 표면형의 반복 언급만 하나로 접는다 —
                        # '사용자 테이블'과 '주문 테이블'은 head가 같아도 서로 다른 후보
                        seen, unique = set(), []
                        for c in ranked:
                            if c.phrase.text not in seen:
                                seen.add(c.phrase.text)
                                unique.append(c)
                        if len(unique) >= 2 and (unique[0].score - unique[1].score) < cfg["threshold"]:
                            yield Diagnostic(
                                rule="REF101", severity="warning",
                                message=f"'{ref.text}'의 지시 대상이 불명확합니다.",
                                range=ref.range,
                                candidates=[
                                    Candidate(text=c.phrase.text, score=c.score)
                                    for c in unique[:3]
                                ],
                            )
                    window.append(sent)
