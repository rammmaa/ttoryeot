from pathlib import Path

from ttoryeot.runner import run_workspace


def test_workspace_diagnostics(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "pipeline.md").write_text(
        "# Pipeline\n\n"
        "데이터세트란 단일 테이블이다.\n\n"
        "사용자 테이블과 주문 테이블을 결합합니다.\n\n"
        "해당 데이터를 저장합니다.\n",
        encoding="utf-8",
    )
    (docs / "glossary.md").write_text(
        "# Glossary\n\n데이터세트란 분석 가능한 테이블의 집합이다.\n",
        encoding="utf-8",
    )
    (docs / "deploy.md").write_text(
        "# Deploy\n\n데이터셋을 운영 환경에 배포합니다.\n",
        encoding="utf-8",
    )
    (docs / "clean.md").write_text(
        "# Clean\n\n결합 결과를 저장합니다.\n",
        encoding="utf-8",
    )
    terms = tmp_path / "terms.yaml"
    terms.write_text(
        "terms:\n"
        "  - canonical: 데이터세트\n"
        "    aliases: [데이터셋, 데이터 세트]\n",
        encoding="utf-8",
    )

    diags = run_workspace(tmp_path, terms, {})
    got = {(d.rule, d.range.file, d.range.start_line) for d in diags}
    expected = {
        ("TERM102", "docs/pipeline.md", 3),
        ("REF101", "docs/pipeline.md", 7),
        ("TERM101", "docs/deploy.md", 3),
    }

    assert got == expected
    assert not [d for d in diags if d.range.file == "docs/clean.md"]
