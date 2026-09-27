from typer.testing import CliRunner

from ttoryeot.cli import app


def test_lint_rejects_missing_root(tmp_path):
    result = CliRunner().invoke(app, ["lint", str(tmp_path / "missing")])

    assert result.exit_code == 2
    assert "existing directory" in result.output


def test_lint_rejects_missing_term_dictionary(tmp_path):
    result = CliRunner().invoke(
        app,
        ["lint", str(tmp_path), "--terms", str(tmp_path / "missing.yaml")],
    )

    assert result.exit_code == 2
    assert "existing file" in result.output
