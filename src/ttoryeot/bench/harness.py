import json
from pathlib import Path

from pydantic import BaseModel

from typing import Callable

from ttoryeot.bench.baselines import (
    NaiveReferenceBaseline,
    RegexBaseline,
    SubstitutionBaseline,
)
from ttoryeot.bench.engine import BenchEngine
from ttoryeot.bench.schema import SentenceItem, load_items
from ttoryeot.bench.scoring import RuleScore, score_items

# 값은 인자 없는 팩토리 — 클래스도, Task 13의 지연 임포트 함수도 등록 가능
ENGINES: dict[str, Callable[[], BenchEngine]] = {
    "baseline-subst": SubstitutionBaseline,
    "baseline-regex": RegexBaseline,
    "baseline-naive-ref": NaiveReferenceBaseline,
}


def _make_ttoryeot() -> BenchEngine:
    from ttoryeot.bench.adapter import TtoryeotEngine

    return TtoryeotEngine()


ENGINES["ttoryeot"] = _make_ttoryeot  # 값이 팩토리이므로 run_and_save의 `ENGINES[engine_name]()` 호출과 호환


class BenchResult(BaseModel):
    engine: str
    n_items: int
    scores: dict[str, RuleScore]


def run_engine(engine: BenchEngine, items: list[SentenceItem]) -> BenchResult:
    predictions = {item.id: engine.predict(item) for item in items}
    return BenchResult(
        engine=engine.name, n_items=len(items), scores=score_items(items, predictions)
    )


def run_and_save(engine_name: str, data_path: Path, out_dir: Path) -> BenchResult:
    engine = ENGINES[engine_name]()
    result = run_engine(engine, load_items(data_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{engine_name}.json").write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
