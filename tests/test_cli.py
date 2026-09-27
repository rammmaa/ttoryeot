from typer.testing import CliRunner

from ttoryeot.cli import app


def test_lint_rejects_missing_root(tmp_path):
    result = CliRunner().invoke(app, ["lint", str(tmp_path / "missing")])

    assert result.exit_code == 2
    assert "existing directory" in result.output


