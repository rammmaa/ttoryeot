from typing import TYPE_CHECKING, Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel

from ttoryeot.diagnostics.models import Diagnostic

if TYPE_CHECKING:
    from ttoryeot.ir.models import WorkspaceIR


class AnalysisContext(BaseModel):
    # 부분 config 주입이 계약이다: 분석기는 자기 섹션을 반드시
    # `{**DEFAULTS, **(ctx.config.get("<섹션>") or {})}` 꼴로 기본값 위에 겹쳐
    # 읽어야 한다 — ctx.config를 완전한 설정으로 가정하고 직접 인덱싱하면
    # 어댑터의 부분 주입·YAML의 빈 섹션에서 깨진다.
    config: dict[str, Any] = {}


@runtime_checkable
class Analyzer(Protocol):
    rule_ids: tuple[str, ...]

    def analyze(self, ws: "WorkspaceIR", ctx: AnalysisContext) -> Iterable[Diagnostic]: ...
