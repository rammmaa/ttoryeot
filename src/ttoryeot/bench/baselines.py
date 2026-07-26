import re

from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.rules_data import DEMONSTRATIVES, REGEX_RULES, SUBSTITUTIONS
from ttoryeot.bench.schema import SentenceItem


class SubstitutionBaseline:
    name = "baseline-subst"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        preds = []
        for wrong, (_fix, category) in SUBSTITUTIONS.items():
            start = 0
            while (idx := item.text.find(wrong, start)) != -1:
                preds.append(Prediction(span=(idx, idx + len(wrong)), category=category))
                start = idx + len(wrong)
        return preds


class RegexBaseline:
    name = "baseline-regex"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        preds = []
        for pattern, category in REGEX_RULES:
            for m in re.finditer(pattern, item.text):
                preds.append(Prediction(span=(m.start(), m.end()), category=category))
        return preds


_REF_PATTERN = re.compile(
    rf"(?:{'|'.join(DEMONSTRATIVES)})\s+[가-힣A-Za-z]+?(?=[을를에과와]|\s|$)"
)


class NaiveReferenceBaseline:
    name = "baseline-naive-ref"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        return [
            Prediction(span=(m.start(), m.end()), category="ambiguous_reference")
            for m in _REF_PATTERN.finditer(item.text)
        ]
