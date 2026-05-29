from collections import defaultdict

from pydantic import BaseModel, computed_field

from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.schema import SentenceItem


def spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


class RuleScore(BaseModel):
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @computed_field
    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @computed_field
    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @computed_field
    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def score_items(
    items: list[SentenceItem], predictions: dict[str, list[Prediction]]
) -> dict[str, RuleScore]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for item in items:
        preds = list(predictions.get(item.id, []))
        matched_preds: set[int] = set()
        for ann in item.annotations:
            hit = None
            for i, p in enumerate(preds):
                if i in matched_preds:
                    continue
                if p.category == ann.category and spans_overlap(p.span, ann.span):
                    hit = i
                    break
            if hit is not None:
                matched_preds.add(hit)
                counts[ann.category]["tp"] += 1
            else:
                counts[ann.category]["fn"] += 1
        for i, p in enumerate(preds):
            if i not in matched_preds:
                counts[p.category]["fp"] += 1
    scores = {cat: RuleScore(**c) for cat, c in counts.items()}
    scores["__total__"] = RuleScore(
        tp=sum(s.tp for s in scores.values()),
        fp=sum(s.fp for s in scores.values()),
        fn=sum(s.fn for s in scores.values()),
    )
    return scores
