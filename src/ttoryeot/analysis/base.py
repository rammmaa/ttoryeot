from typing import TYPE_CHECKING, Any, Iterable, Protocol, runtime_checkable

from pydantic import BaseModel

from ttoryeot.diagnostics.models import Diagnostic

if TYPE_CHECKING:
    from ttoryeot.ir.models import WorkspaceIR


class AnalysisContext(BaseModel):
    config: dict[str, Any] = {}


@runtime_checkable
class Analyzer(Protocol):
    rule_ids: tuple[str, ...]

    def analyze(self, ws: "WorkspaceIR", ctx: AnalysisContext) -> Iterable[Diagnostic]: ...
