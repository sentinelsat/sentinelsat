from os import environ

import pytest
from click.testing import CliRunner

from sentinelsat.scripts.cli import cli
from .shared import my_vcr

_api_auth = [environ.get('SENTINEL_USER', "user"), environ.get('SENTINEL_PASSWORD', "pw")]


@my_vcr.use_cassette
@pytest.mark.scihub
def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson'],
        catch_exceptions=False
    )

    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '--url', 'https://scihub.copernicus.eu/dhus/'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '-q', 'producttype=GRD,polarisationmode=HH'],
        catch_exceptions=False
    )
    assert result.exit_code == 0


@my_vcr.use_cassette
@pytest.mark.scihub
def test_returned_filesize():
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '--url', 'https://scihub.copernicus.eu/dhus/',
         '-s', '20141205',
         '-e', '20141208',
         '-q', 'producttype=GRD'],
        catch_exceptions=False
    )
    expected = "1 scenes found with a total size of 0.50 GB"
    assert result.output.split("\n")[-2] == expected

    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '--url', 'https://scihub.copernicus.eu/dhus/',
         '-s', '20140101',
         '-e', '20141231',
         '-q', 'producttype=GRD'],
        catch_exceptions=False
    )
    expected = "20 scenes found with a total size of 11.06 GB"

    assert result.output.split("\n")[-2] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_cloud_flag_url():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '-c', "10"],
        catch_exceptions=False
    )

    expected = "Product 6ed0b7de-3435-43df-98bf-ad63c8d077ef - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.47 GB"
    assert result.output.split("\n")[0] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel1_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel1'],
        catch_exceptions=False
    )

    expected = "Product 6a62313b-3d6f-489e-bfab-71ce8d7f57db - Date: 2015-12-24T09:40:34.129Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.7 GB"
    assert result.output.split("\n")[4] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel2_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['search'] +
        _api_auth +
        ['tests/map.geojson',
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel2'],
        catch_exceptions=False
    )

    expected = "Product 91c2503c-3c58-4a8c-a70b-207b128e6833 - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.73 GB"
    assert result.output.split("\n")[2] == expected
