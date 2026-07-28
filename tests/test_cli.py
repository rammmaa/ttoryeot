import json
from pathlib import Path

from typer.testing import CliRunner

from ttoryeot.cli import app

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "corpus" / "fixtures" / "data-platform"
SAMPLE = REPO / "benchmark" / "data" / "sample-sentences.jsonl"

runner = CliRunner()


def test_lint_reports_fixture_diagnostics():
    res = runner.invoke(
        app, ["lint", str(FIXTURE), "--terms", str(FIXTURE / "terms.yaml")]
    )
    assert res.exit_code == 1
    assert "TERM101" in res.output
    assert "REF101" in res.output


def test_lint_config_reaches_analyzer(tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("reference:\n  threshold: 0.0\n", encoding="utf-8")
    res = runner.invoke(
        app,
        ["lint", str(FIXTURE), "--terms", str(FIXTURE / "terms.yaml"),
         "--config", str(cfg)],
    )
    assert res.exit_code == 1  # TERM 진단은 남는다
    assert "REF101" not in res.output


def test_bench_run_missing_data_exits_2_with_guidance(tmp_path):
    res = runner.invoke(
        app,
        ["bench", "run", "--engine", "ttoryeot",
         "--data", str(tmp_path / "sentences.jsonl"), "--out-dir", str(tmp_path)],
    )
    assert res.exit_code == 2
    assert "bench convert" in res.output


def test_bench_run_unknown_engine_exits_2_with_engine_list(tmp_path):
    res = runner.invoke(
        app,
        ["bench", "run", "--engine", "없는엔진",
         "--data", str(SAMPLE), "--out-dir", str(tmp_path)],
    )
    assert res.exit_code == 2
    assert "ttoryeot" in res.output
    assert "baseline-regex" in res.output


def test_bench_run_and_report_smoke(tmp_path):
    res = runner.invoke(
        app,
        ["bench", "run", "--engine", "baseline-regex",
         "--data", str(SAMPLE), "--out-dir", str(tmp_path)],
    )
    assert res.exit_code == 0
    assert (tmp_path / "baseline-regex.json").exists()

    res = runner.invoke(app, ["bench", "report", "--results-dir", str(tmp_path)])
    assert res.exit_code == 0
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "baseline-regex" in report


def test_bench_convert_smoke(tmp_path):
    csv_path = tmp_path / "survey.csv"
    csv_path.write_text(
        "원문,수정안,오류 분류,판정 이유,근거 URL,확신도,출처,문서 장르\n"
        "해당 데이터를 저장합니다.,조인 결과를 저장합니다.,"
        "ambiguous_reference,후보 다수,,high,survey,guide\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.jsonl"
    res = runner.invoke(
        app,
        ["bench", "convert", str(csv_path),
         str(REPO / "benchmark" / "raw" / "columns.example.yaml"), str(out)],
    )
    assert res.exit_code == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["annotations"][0]["category"] == "ambiguous_reference"
