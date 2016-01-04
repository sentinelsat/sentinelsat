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
        '--url', 'https://scihub.copernicus.eu/dhus/'
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

def test_returned_filesize():
    runner = CliRunner()

    result = runner.invoke(cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/dhus/',
        '-s', '20141205',
        '-e', '20141208',
        '-q', 'producttype=GRD'
        ])
    expected = "1 scenes found with a total size of 0.50 GB"
    assert result.output.split("\n")[-2] == expected

    result = runner.invoke(cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/dhus/',
        '-s', '20140101',
        '-e', '20141231',
        '-q', 'producttype=GRD'
        ])
    expected = "13 scenes found with a total size of 7.23 GB"
    assert result.output.split("\n")[-2] == expected
