from click.testing import CliRunner

from os import environ

from sentinelsat.scripts.cli import cli


def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson'
        ])
    assert result.exit_code == 0

    result = runner.invoke(cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.esa.int/dhus/'
        ])
    assert result.exit_code == 0

    result = runner.invoke(cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '-q', 'producttype=GRD,polarisationmode=HH'
        ])
    assert result.exit_code == 0
