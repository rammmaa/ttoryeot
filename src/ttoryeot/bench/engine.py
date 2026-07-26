from typing import Protocol

from pydantic import BaseModel

from ttoryeot.bench.schema import SentenceItem


class Prediction(BaseModel):
    span: tuple[int, int]  # item.text 기준 문자 오프셋
    category: str


class BenchEngine(Protocol):
    name: str

    def predict(self, item: SentenceItem) -> list[Prediction]: ...
