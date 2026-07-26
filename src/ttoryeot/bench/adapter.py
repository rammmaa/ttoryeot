from ttoryeot.analysis.base import AnalysisContext
from ttoryeot.analysis.references.analyzer import ReferenceAnalyzer
from ttoryeot.analysis.terms.analyzer import TermAnalyzer
from ttoryeot.analysis.terms.dictionary import TermEntry
from ttoryeot.bench.engine import Prediction
from ttoryeot.bench.schema import SentenceItem
from ttoryeot.ir.models import WorkspaceIR
from ttoryeot.parsing.lowering import lower_document
from ttoryeot.parsing.workspace import get_kiwi

RULE_CATEGORY = {
    "REF101": "ambiguous_reference",
    "TERM100": "term_inconsistency",
    "TERM101": "term_inconsistency",
    "TERM102": "term_definition_conflict",
}

# 트랙 1용 시드 용어 사전 — 조사표 도착 시 확장
SEED_TERMS = [TermEntry(canonical="데이터세트", aliases=["데이터셋", "데이터 세트"])]


class TtoryeotEngine:
    name = "ttoryeot"

    def predict(self, item: SentenceItem) -> list[Prediction]:
        prefix = item.context_before + "\n\n" if item.context_before else ""
        source = prefix + item.text
        doc = lower_document("item.md", source, get_kiwi())
        ws = WorkspaceIR(root=".", documents=[doc])
        ctx = AnalysisContext()
        base = len(prefix)
        preds = []
        for analyzer in (TermAnalyzer(SEED_TERMS), ReferenceAnalyzer()):
            for d in analyzer.analyze(ws, ctx):
                start = d.range.start_offset - base
                end = d.range.end_offset - base
                if start < 0 or d.rule not in RULE_CATEGORY:
                    continue
                preds.append(Prediction(span=(start, min(end, len(item.text))),
                                        category=RULE_CATEGORY[d.rule]))
        return preds
