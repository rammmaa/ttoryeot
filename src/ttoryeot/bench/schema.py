import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator


class Evidence(BaseModel):
    source: str
    url: str | None = None


class Annotation(BaseModel):
    span: tuple[int, int]
    category: str
    severity: Literal["error", "warning", "info"]
    correction: str | None = None
    rationale: str | None = None
    evidence: Evidence | None = None
    confidence: Literal["high", "medium", "low"]


class SentenceItem(BaseModel):
    id: str
    source: str
    document_type: str
    context_before: str = ""
    text: str
    context_after: str = ""
    annotations: list[Annotation] = []

    @model_validator(mode="after")
    def _spans_within_text(self) -> "SentenceItem":
        for ann in self.annotations:
            start, end = ann.span
            if not (0 <= start < end <= len(self.text)):
                raise ValueError(f"span {ann.span} out of range for text len {len(self.text)}")
        return self


def load_items(path: Path) -> list[SentenceItem]:
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(SentenceItem.model_validate_json(line))
    return items


def export_json_schema(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = SentenceItem.model_json_schema()
    (out_dir / "sentence-item.schema.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
    )
