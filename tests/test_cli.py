from click.testing import CliRunner

from os import environ
import pytest

from sentinelsat.scripts.cli import cli


@pytest.mark.scihub
def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson']
        )

    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/dhus/']
        )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '-q', 'producttype=GRD,polarisationmode=HH']
        )
    assert result.exit_code == 0


@pytest.mark.scihub
def test_returned_filesize():
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/dhus/',
        '-s', '20141205',
        '-e', '20141208',
        '-q', 'producttype=GRD']
        )
    expected = "1 scenes found with a total size of 0.50 GB"
    assert result.output.split("\n")[-2] == expected

    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/dhus/',
        '-s', '20140101',
        '-e', '20141231',
        '-q', 'producttype=GRD']
        )
    expected = "20 scenes found with a total size of 11.06 GB"
    assert result.output.split("\n")[-2] == expected


@pytest.mark.scihub
def test_cloud_flag_url():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/apihub/',
        '-s', '20151219',
        '-e', '20151228',
        '-c', "10"]
        )

    expected = "Product 6ed0b7de-3435-43df-98bf-ad63c8d077ef - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.47 GB"
    assert result.output.split("\n")[0] == expected


@pytest.mark.scihub
def test_sentinel1_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/apihub/',
        '-s', '20151219',
        '-e', '20151228',
        '--sentinel1']
        )

    expected = "Product 6a62313b-3d6f-489e-bfab-71ce8d7f57db - Date: 2015-12-24T09:40:34.129Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.7 GB"
    assert result.output.split("\n")[4] == expected


@pytest.mark.scihub
def test_sentinel2_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search',
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'tests/map.geojson',
        '--url', 'https://scihub.copernicus.eu/apihub/',
        '-s', '20151219',
        '-e', '20151228',
        '--sentinel2']
        )

    expected = "Product 91c2503c-3c58-4a8c-a70b-207b128e6833 - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.73 GB"
    assert result.output.split("\n")[2] == expected
