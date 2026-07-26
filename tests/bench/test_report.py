import json
from pathlib import Path

from ttoryeot.bench.report import write_report


def result(engine, cat, tp, fp, fn):
    return {
        "engine": engine, "n_items": 10,
        "scores": {
            cat: {"tp": tp, "fp": fp, "fn": fn},
            "__total__": {"tp": tp, "fp": fp, "fn": fn},
        },
    }


def test_write_report(tmp_path: Path):
    (tmp_path / "baseline-regex.json").write_text(
        json.dumps(result("baseline-regex", "spacing", 5, 5, 0)))
    (tmp_path / "ttoryeot.json").write_text(
        json.dumps(result("ttoryeot", "spacing", 5, 1, 0)))
    out = write_report(tmp_path)
    md = out.read_text(encoding="utf-8")
    assert "baseline-regex" in md and "ttoryeot" in md
    assert "spacing" in md and "0.833" in md  # ttoryeot precision 5/6
