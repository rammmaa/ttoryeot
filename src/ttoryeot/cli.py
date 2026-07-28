from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)
bench_app = typer.Typer(no_args_is_help=True)
app.add_typer(bench_app, name="bench")


@bench_app.command()
def convert(csv_path: Path, mapping: Path, out: Path) -> None:
    from ttoryeot.bench.convert import convert_csv

    n = convert_csv(csv_path, mapping, out)
    typer.echo(f"{n}개 항목 변환 완료 → {out}")


@bench_app.command()
def run(
    data: Path = typer.Option(Path("benchmark/data/sentences.jsonl")),
    engine: str = typer.Option(...),
    out_dir: Path = typer.Option(Path("benchmark/results")),
) -> None:
    from ttoryeot.bench.harness import ENGINES, run_and_save

    if engine not in ENGINES:
        typer.echo(
            f"미등록 엔진 '{engine}' — 사용 가능: {', '.join(sorted(ENGINES))}",
            err=True,
        )
        raise typer.Exit(code=2)
    if not data.exists():
        typer.echo(
            f"벤치 데이터가 없습니다: {data}\n"
            f"조사표 CSV를 먼저 변환하세요: "
            f"ttoryeot bench convert <csv> <columns.yaml> {data}",
            err=True,
        )
        raise typer.Exit(code=2)
    result = run_and_save(engine, data, out_dir)
    total = result.scores["__total__"]
    typer.echo(
        f"{engine}: P={total.precision:.3f} R={total.recall:.3f} F1={total.f1:.3f}"
    )


@bench_app.command()
def report(results_dir: Path = typer.Option(Path("benchmark/results"))) -> None:
    from ttoryeot.bench.report import write_report

    out = write_report(results_dir)
    typer.echo(f"리포트 생성 → {out}")


@app.command()
def lint(
    root: Path,
    terms: Path | None = typer.Option(None, help="용어 사전 YAML"),
    config: Path | None = typer.Option(None, help="설정 YAML (default.yaml 위에 덮어씀)"),
) -> None:
    from ttoryeot.config import load_config
    from ttoryeot.runner import run_workspace

    diags = run_workspace(root, terms, load_config(config))
    for d in sorted(diags, key=lambda d: (d.range.file, d.range.start_line)):
        typer.echo(f"{d.range.file}:{d.range.start_line} {d.rule} {d.message}")
        for c in d.candidates:
            typer.echo(f"    후보 {c.score:.2f}  {c.text}")
    if diags:
        raise typer.Exit(code=1)
