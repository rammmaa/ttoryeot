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


def _maximum_matching(
    adj_list: list[list[int]], n_ann: int, n_pred: int
) -> tuple[list[int], set[int]]:
    """Find maximum bipartite matching using augmenting paths.

    Args:
        adj_list: adj_list[i] = list of prediction indices that annotation i can match to
        n_ann: number of annotations
        n_pred: number of predictions

    Returns:
        (match_ann, matched_pred_indices) where:
        - match_ann[i] = prediction index matched to annotation i, or -1 if unmatched
        - matched_pred_indices = set of prediction indices that are matched
    """
    match_pred = [-1] * n_pred  # match_pred[j] = annotation index matched to pred j, or -1
    match_ann = [-1] * n_ann    # match_ann[i] = prediction index matched to ann i, or -1

    def dfs(ann_idx: int, visited: set[int]) -> bool:
        """Try to find an augmenting path starting from annotation ann_idx."""
        for pred_idx in adj_list[ann_idx]:
            if pred_idx in visited:
                continue
            visited.add(pred_idx)

            # If pred is unmatched or we can augment the path from its current match
            if match_pred[pred_idx] == -1 or dfs(match_pred[pred_idx], visited):
                match_ann[ann_idx] = pred_idx
                match_pred[pred_idx] = ann_idx
                return True
        return False

    for ann_idx in range(n_ann):
        visited: set[int] = set()
        dfs(ann_idx, visited)

    matched_pred_indices = {i for i in range(n_pred) if match_pred[i] != -1}
    return match_ann, matched_pred_indices


def score_items(
    items: list[SentenceItem], predictions: dict[str, list[Prediction]]
) -> dict[str, RuleScore]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for item in items:
        preds = list(predictions.get(item.id, []))
        n_ann = len(item.annotations)
        n_pred = len(preds)

        if n_ann == 0 and n_pred == 0:
            continue

        # Build bipartite graph: edge exists if category matches and spans overlap
        adj_list = []
        for ann in item.annotations:
            matches = []
            for i, p in enumerate(preds):
                if p.category == ann.category and spans_overlap(p.span, ann.span):
                    matches.append(i)
            adj_list.append(matches)

        # Find maximum matching
        match_ann, matched_pred_indices = _maximum_matching(adj_list, n_ann, n_pred)

        # Count TP, FN, FP
        for ann_idx, pred_idx in enumerate(match_ann):
            ann = item.annotations[ann_idx]
            if pred_idx != -1:
                counts[ann.category]["tp"] += 1
            else:
                counts[ann.category]["fn"] += 1

        for pred_idx, p in enumerate(preds):
            if pred_idx not in matched_pred_indices:
                counts[p.category]["fp"] += 1

    scores = {cat: RuleScore(**c) for cat, c in counts.items()}
    scores["__total__"] = RuleScore(
        tp=sum(s.tp for s in scores.values()),
        fp=sum(s.fp for s in scores.values()),
        fn=sum(s.fn for s in scores.values()),
    )
    return scores
