"""AMB101 — 명사 연쇄(noun string) 모호성.

명사를 조사 없이 길게 나열하면 단어 간 연결 관계(수식·소유·병렬)가 표면에서
사라진다. 상한의 근거는 독립적인 두 계보가 같은 값에 수렴한다는 것이다 —
ASD-STE100 Rule 2.1(복합명사 3단어 이하)과 미 연방 plain language 지침
avoid-noun-strings(명사 3개 초과는 불가독). 한국어는 핵어 후치인 데다 조사를
생략한 명사 나열이 관용이라 연쇄가 영어보다 길게 자란다 — 상세는
docs/research/2026-07-29-related-work-verified.md §4.

탐지 자체는 IR을 재활용한다: lowering의 명사구(연속 NNG|NNP|SL 런)가 이미
'조사 없이 이어진 명사 나열'의 정의와 일치하므로, 어절 수만 세면 된다.
코드 스팬 안의 명사구는 lowering이 이미 후보에서 제외한다(식별자 나열은
산문 모호성이 아니다). 재작성 제안이 아니라 관계 명시를 권하는 info인 이유:
어느 연결이 옳은지는 작성자만 알며, 도구가 확정하면 그 자체가 새 오류원이 된다.
"""

from typing import Iterable

from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.config import default_config
from ttoryeot.diagnostics.models import Diagnostic
from ttoryeot.ir.models import WorkspaceIR

DEFAULTS = default_config()["ambiguity"]


class NounChainAnalyzer:
    rule_ids = ("AMB101",)

    def analyze(self, ws: WorkspaceIR, ctx: AnalysisContext) -> Iterable[Diagnostic]:
        cfg = {**DEFAULTS, **(ctx.config.get("ambiguity") or {})}
        # 발화율 실측 전이라 opt-in — runner는 이 분석기를 항상 구성하므로
        # (known_rules에 AMB101이 있어야 억제 프라그마가 INT002 오보 없이 먹힌다)
        # off는 여기서 no-op으로 처리한다. TERM103~105와 같은 패턴.
        if not cfg.get("noun_chain"):
            return
        max_eojeol = int(cfg["max_noun_chain_eojeol"])
        for _doc, _block, sent in ws.iter_sentences():
            for np in sent.noun_phrases:
                # 어절 수는 공백 구분으로 센다 — 명사구 런은 단일 공백·단일
                # 소프트 줄바꿈만 허용하므로 split()이 곧 어절 분리다.
                n = len(np.text.split())
                if n <= max_eojeol:
                    continue
                # 라틴 전용 런(영어 제목·영어 문장 인용)은 한국어 명사 나열
                # 모호성이 아니다 — 실측에서 발화 노이즈의 최대 축(fe-news 64%,
                # react 71%)이었다. 한글이 최소 한 자는 있어야 대상이다.
                if not any("가" <= ch <= "힣" for ch in np.text):
                    continue
                yield Diagnostic(
                    rule="AMB101", severity="info",
                    message=(
                        f"'{np.text}'은(는) {n}어절 명사 나열입니다 — 단어 간 "
                        f"연결 관계가 흐려집니다. 조사나 수식으로 관계를 "
                        f"명시하세요."
                    ),
                    # range는 np.range 그대로 — 오프셋 불변식(원문 슬라이스 ==
                    # 명사구 텍스트)을 그대로 물려받는다.
                    range=np.range,
                )
