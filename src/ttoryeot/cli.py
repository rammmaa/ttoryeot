from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)
bench_app = typer.Typer(no_args_is_help=True)
app.add_typer(bench_app, name="bench")


@bench_app.command()
def convert(csv_path: Path, mapping: Path, out: Path) -> None:
    from ttoryeot.bench.convert import convert_csv

    try:
        n = convert_csv(csv_path, mapping, out)
    except (ValueError, OSError) as exc:
        typer.echo(f"변환 실패: {exc}", err=True)
        raise typer.Exit(code=2)
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
def nocuity(
    instances: Path = typer.Argument(..., help="인스턴스 JSONL"),
    forms: list[Path] = typer.Argument(..., help="판정자별 서식 .md (여러 개)"),
    flagged: Path = typer.Option(..., help="엔진이 경고한 id 목록 JSON"),
) -> None:
    """인간 판정 분포로 REF101을 채점한다 (τ 스윕 + F2)."""
    import json as _json

    from ttoryeot.bench.nocuity import (
        load_instances,
        merge_judgments,
        parse_judgment_form,
        sweep,
    )

    for p in [instances, flagged, *forms]:
        if not p.is_file():
            typer.echo(f"파일이 없습니다: {p}", err=True)
            raise typer.Exit(code=2)
    items = merge_judgments(
        load_instances(instances),
        [parse_judgment_form(f.read_text(encoding="utf-8")) for f in forms],
    )
    n_judged = sum(1 for i in items if i.judgments)
    if not n_judged:
        typer.echo("판정이 하나도 없습니다 — 서식의 체크박스를 [x]로 채우세요", err=True)
        raise typer.Exit(code=2)
    flagged_ids = set(_json.loads(flagged.read_text(encoding="utf-8")))

    typer.echo(f"인스턴스 {len(items)}건 (판정 있음 {n_judged}건), 판정자 {len(forms)}명")
    typer.echo("| τ | nocuous | P | R | F2 |")
    typer.echo("|---|---|---|---|---|")
    for s in sweep(items, flagged_ids):
        typer.echo(
            f"| {s.tau:.2f} | {s.n_nocuous}/{s.n_total} | {s.precision:.3f} | "
            f"{s.recall:.3f} | {s.f2:.3f} |"
        )


@bench_app.command()
def report(results_dir: Path = typer.Option(Path("benchmark/results"))) -> None:
    from ttoryeot.bench.report import write_report

    if not results_dir.is_dir():
        typer.echo(f"결과 디렉터리가 존재하지 않습니다: {results_dir}", err=True)
        raise typer.Exit(code=2)
    if not any(results_dir.glob("*.json")):
        typer.echo(
            f"결과 JSON이 없습니다: {results_dir} — 먼저 ttoryeot bench run을 실행하세요",
            err=True,
        )
        raise typer.Exit(code=2)
    out = write_report(results_dir)
    typer.echo(f"리포트 생성 → {out}")


@app.command()
def lint(
    root: Path,
    terms: Path | None = typer.Option(None, help="용어 사전 YAML"),
    config: Path | None = typer.Option(None, help="설정 YAML (default.yaml 위에 덮어씀)"),
    explain: bool = typer.Option(False, help="진단 근거(자질별 점수 등)를 함께 출력"),
) -> None:
    from ttoryeot.config import ConfigError, load_config
    from ttoryeot.runner import run_workspace

    if not root.is_dir():
        typer.echo(f"루트 디렉터리가 존재하지 않습니다: {root}", err=True)
        raise typer.Exit(code=2)
    if terms is not None and not terms.is_file():
        # 오타가 TermAnalyzer의 조용한 탈락(TERM 무진단 통과)으로 위장되면 안 된다
        typer.echo(f"용어 사전 파일을 찾을 수 없습니다: {terms}", err=True)
        raise typer.Exit(code=2)
    try:
        cfg = load_config(config)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2)
    diags = run_workspace(root, terms, cfg)
    for d in sorted(diags, key=lambda d: (d.range.file, d.range.start_line)):
        typer.echo(f"{d.range.file}:{d.range.start_line} {d.rule} {d.message}")
        for c in d.candidates:
            typer.echo(f"    후보 {c.score:.2f}  {c.text}")
        if explain and d.evidence:
            typer.echo(f"    {d.evidence}")
    if diags:
        raise typer.Exit(code=1)
