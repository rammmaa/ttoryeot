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
    from ttoryeot.bench.harness import run_and_save

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
