import json
from pathlib import Path

from ttoryeot.bench.harness import BenchResult


def write_report(results_dir: Path) -> Path:
    results = [
        BenchResult.model_validate(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(results_dir.glob("*.json"))
    ]
    lines = ["# 벤치마크 리포트", ""]
    categories = sorted({c for r in results for c in r.scores if c != "__total__"})
    header = "| engine | " + " | ".join(categories) + " | total F1 |"
    sep = "|---" * (len(categories) + 2) + "|"
    lines += ["P/R/F1 per category:", "", header, sep]
    for r in results:
        cells = []
        for cat in categories:
            s = r.scores.get(cat)
            cells.append(f"{s.precision:.3f}/{s.recall:.3f}/{s.f1:.3f}" if s else "—")
        total = r.scores["__total__"]
        lines.append(f"| {r.engine} | " + " | ".join(cells) + f" | {total.f1:.3f} |")
    out = results_dir / "report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
