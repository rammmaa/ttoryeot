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


def test_lint_explain_shows_feature_breakdown():
    plain = runner.invoke(app, ["lint", str(FIXTURE)])
    assert "후보 점수 근거" not in plain.output
    explained = runner.invoke(app, ["lint", str(FIXTURE), "--explain"])
    assert "후보 점수 근거" in explained.output
    assert "head_match" in explained.output


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


def test_lint_missing_config_exits_2(tmp_path):
    res = runner.invoke(
        app, ["lint", str(FIXTURE), "--config", str(tmp_path / "nope.yaml")]
    )
    assert res.exit_code == 2
    assert "설정" in res.output


def test_lint_null_section_config_runs_normally(tmp_path):
    cfg = tmp_path / "null.yaml"
    cfg.write_text("reference:\n", encoding="utf-8")
    res = runner.invoke(
        app,
        ["lint", str(FIXTURE), "--terms", str(FIXTURE / "terms.yaml"),
         "--config", str(cfg)],
    )
    assert res.exit_code == 1  # 크래시가 아니라 기본 설정으로 정상 진단
    assert "REF101" in res.output


def test_lint_missing_terms_exits_2(tmp_path):
    """--terms 오타가 TermAnalyzer의 조용한 탈락(TERM 무진단 통과)으로 위장되면
    안 된다 — 루트 가드와 동일한 원칙."""
    res = runner.invoke(
        app, ["lint", str(FIXTURE), "--terms", str(tmp_path / "nope.yaml")]
    )
    assert res.exit_code == 2
    assert "용어 사전" in res.output


def test_lint_missing_root_exits_2(tmp_path):
    """존재하지 않는 루트는 조용한 '클린'(exit 0)이 아니라 명확한 에러여야 한다 —
    경로 오타가 무진단 통과로 위장되는 것을 막는다."""
    res = runner.invoke(app, ["lint", str(tmp_path / "no-such-dir")])
    assert res.exit_code == 2
    assert "존재하지 않" in res.output


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


def test_bench_report_missing_dir_exits_2(tmp_path):
    res = runner.invoke(
        app, ["bench", "report", "--results-dir", str(tmp_path / "nope")]
    )
    assert res.exit_code == 2


def test_bench_report_empty_dir_exits_2(tmp_path):
    res = runner.invoke(app, ["bench", "report", "--results-dir", str(tmp_path)])
    assert res.exit_code == 2
    assert "bench run" in res.output


def test_bench_convert_wrong_text_column_exits_2(tmp_path):
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("잘못된헤더\n값\n", encoding="utf-8")
    res = runner.invoke(
        app,
        ["bench", "convert", str(csv_path),
         str(REPO / "benchmark" / "raw" / "columns.example.yaml"),
         str(tmp_path / "o.jsonl")],
    )
    assert res.exit_code == 2
    assert "원문" in res.output  # 어떤 열을 찾다 실패했는지 알려준다


def test_bench_convert_incomplete_mapping_exits_2(tmp_path):
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("원문\n문장입니다.\n", encoding="utf-8")
    mapping = tmp_path / "columns.yaml"
    mapping.write_text("text: 원문\n", encoding="utf-8")
    res = runner.invoke(
        app,
        ["bench", "convert", str(csv_path), str(mapping),
         str(tmp_path / "o.jsonl")],
    )
    assert res.exit_code == 2
    assert "category" in res.output  # 누락 키를 알려준다


def test_bench_convert_malformed_mapping_yaml_exits_2(tmp_path):
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("원문\n문장입니다.\n", encoding="utf-8")
    mapping = tmp_path / "columns.yaml"
    mapping.write_text("text: [unclosed\n", encoding="utf-8")
    res = runner.invoke(
        app,
        ["bench", "convert", str(csv_path), str(mapping),
         str(tmp_path / "o.jsonl")],
    )
    assert res.exit_code == 2
    assert "columns.yaml" in res.output


def test_lint_terms_directory_exits_2(tmp_path):
    """--terms에 디렉터리를 주면 exists()는 통과하지만 read에서 터진다 —
    파일이 아니면 같은 가드로 잡는다."""
    res = runner.invoke(app, ["lint", str(FIXTURE), "--terms", str(tmp_path)])
    assert res.exit_code == 2
    assert "용어 사전" in res.output


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
