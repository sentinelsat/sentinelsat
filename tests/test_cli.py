from click.testing import CliRunner

from sentinelsat.scripts.cli import cli


def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli, ['-a', '0 0,1 1,0 1,0 0', ])
    assert result.exit_code == 0
    assert result.output == "False\nFalse\nFalse\n"
