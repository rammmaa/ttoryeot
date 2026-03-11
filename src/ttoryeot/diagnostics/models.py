from typing import Literal

from pydantic import BaseModel

from ttoryeot.ir.source import SourceRange


class Candidate(BaseModel):
    text: str
    score: float


class Diagnostic(BaseModel):
    rule: str
    severity: Literal["error", "warning", "info"]
    message: str
    range: SourceRange
    candidates: list[Candidate] = []
    evidence: str | None = None
