from os import environ, path
import re

import pytest
import requests_mock
from click.testing import CliRunner

from sentinelsat import InvalidChecksumError, SentinelAPI
from sentinelsat.scripts.cli import cli
from .shared import my_vcr, FIXTURES_DIR

_api_auth = [environ.get('SENTINEL_USER', "user"), environ.get('SENTINEL_PASSWORD', "pw")]

# TODO: change test fictures from subcommands to unified commands
# TODO: include test for --uuid option, with comma separated list.

@my_vcr.use_cassette
@pytest.mark.scihub
def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson')],
        catch_exceptions=False
    )

    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/dhus/'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
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
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
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
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
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
    command = ['--user', _api_auth[0],
     '--password', _api_auth[1],
     '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
     '--url', 'https://scihub.copernicus.eu/apihub/',
     '-s', '20151219',
     '-e', '20151228',
     '-c', '10']

    runner = CliRunner()
    result = runner.invoke(
        cli,
        command + ['--sentinel', '2'],
        catch_exceptions=False
    )

    expected = "Product 6ed0b7de-3435-43df-98bf-ad63c8d077ef - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.47 GB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected
    # For order-by test
    assert '0848f6b8-5730-4759-850e-fc9945d42296' not in re.findall("^Product .+$", result.output, re.M)[1]


    with pytest.raises(ValueError) as excinfo:
        result = runner.invoke(
            cli,
            command + ['--sentinel', '1'],
            catch_exceptions=False
        )

@my_vcr.use_cassette
@pytest.mark.scihub
def test_order_by_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '-c', '10',
         '--sentinel', '2',
         '--order-by', 'cloudcoverpercentage,-beginposition'],
        catch_exceptions=False
    )
    print(result.output)
    assert '0848f6b8-5730-4759-850e-fc9945d42296' in re.findall("^Product .+$", result.output, re.M)[1]


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel1_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel', '1'],
        catch_exceptions=False
    )

    expected = "Product 6a62313b-3d6f-489e-bfab-71ce8d7f57db - Date: 2015-12-24T09:40:34.129Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.7 GB"
    assert re.findall("^Product .+$", result.output, re.M)[4] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel2_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel', '2'],
        catch_exceptions=False
    )

    expected = "Product 91c2503c-3c58-4a8c-a70b-207b128e6833 - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.73 GB"
    assert re.findall("^Product .+$", result.output, re.M)[2] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel3_flag():
    # preliminary Sentinel-3 test using S3 Pre-Ops Hub until data is included in OpenAccessHub
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', 's3guest',
         '--password', 's3guest',
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/s3/',
         '-s', '20161201',
         '-e', '20161202',
         '--sentinel', '3'],
        catch_exceptions=False
    )

    expected = "Product c4a36e6b-4a18-46b4-b2ff-abe7a231a46f - Date: 2016-12-01T13:21:33.755Z, Instrument: OLCI, Mode: , Satellite: Sentinel-3, Size: 721.66 MB"
    assert re.findall("^Product .+$", result.output, re.M)[3] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_product_flag():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20161201',
         '-e', '20161202',
         '--producttype', 'SLC'],
        catch_exceptions=False
    )

    expected = "Product 2223103a-3754-473d-9a29-24ef8efa2880 - Date: 2016-12-01T09:30:22.149Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.98 GB"
    assert re.findall("^Product .+$", result.output, re.M)[3] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_instrument_flag():
    # preliminary Sentinel-3 test using S3 Pre-Ops Hub until data is included in OpenAccessHub
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', 's3guest',
         '--password', 's3guest',
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/s3/',
         '-s', '20161201',
         '-e', '20161202',
         '--instrument', 'SRAL'],
        catch_exceptions=False
    )

    expected = "Product 50d27cb5-70da-41c9-b0f3-023cfb25d781 - Date: 2016-12-01T13:13:17.65Z, Instrument: SRAL, Mode: , Satellite: Sentinel-3, Size: 76.62 MB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_limit_flag():
    runner = CliRunner()
    limit = 15
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20161201',
         '-e', '20161230',
         '--limit', str(limit)],
        catch_exceptions=False
    )
    num_products = len(re.findall("^Product ", result.output, re.MULTILINE))
    assert num_products == limit


@my_vcr.use_cassette
@pytest.mark.scihub
def test_uuid_search():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--uuid', 'd8340134-878f-4891-ba4f-4df54f1e3ab4'],
        catch_exceptions=False
    )

    expected = "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A - 0.12 MB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_name_search():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--name', 'S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A'],
        catch_exceptions=False
    )

    expected = "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - Date: 2015-05-26T21:10:28.984Z, Instrument: SAR-C SAR, Mode: VV, Satellite: Sentinel-1, Size: 10.65 KB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_option_hierarchy():
    # expected hierarchy is producttype > instrument > plattform from most to least specific
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20161201',
         '-e', '20161202',
         '--sentinel', '1',
         '--instrument', 'SAR-C SAR',
         '--producttype', 'S2MSI1C'],
        catch_exceptions=False
    )

    expected = "Product 0e66b563-78d9-4480-9c3d-b64a60cf1a9f - Date: 2016-12-01T14:10:42Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 526.15 MB"
    assert re.findall("^Product .+$", result.output, re.M)[1] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_footprints_cli(tmpdir):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', _api_auth[0],
         '--password', _api_auth[1],
         '--geometry', path.join(FIXTURES_DIR, 'map.geojson'),
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel2',
         '--path', str(tmpdir),
         '--footprints'],
        catch_exceptions=False
    )


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_single(tmpdir):
    runner = CliRunner()

    product_id = '5618ce1b-923b-4df2-81d9-50b53e5aded9'
    command = ['--user', _api_auth[0],
        '--password', _api_auth[1],
        '--uuid', product_id,
        '--download',
        '--path', str(tmpdir)]
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )

    # The file already exists, should not be re-downloaded
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    api = SentinelAPI(*_api_auth)
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force the download to fail by providing an incorrect checksum
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)

        # md5 flag set (implicitly), should raise an exception
        with pytest.raises(InvalidChecksumError) as excinfo:
            result = runner.invoke(
                cli,
                command,
                catch_exceptions=False
            )

    # clean up
    tmpdir.remove()


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_many(tmpdir):
    runner = CliRunner()

    command = ['--user', _api_auth[0],
        '--password', _api_auth[1],
        '--uuid',
        '1f62a176-c980-41dc-b3a1-c735d660c910,5618ce1b-923b-4df2-81d9-50b53e5aded9,d8340134-878f-4891-ba4f-4df54f1e3ab4',
        '--download',
        '--path', str(tmpdir)]

    # Download 3 tiny products
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )

    # Should not re-download
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    product_id = 'd8340134-878f-4891-ba4f-4df54f1e3ab4'
    url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    api = SentinelAPI(*_api_auth)
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force one download to fail
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)

        rqst.get(url, json=json)
        # md5 flag set (implicitly), should raise an exception
        result = runner.invoke(
            cli,
            command,
            catch_exceptions=False
        )
        assert 'is corrupted' in result.output

    assert tmpdir.join('corrupt_scenes.txt').check()
    with tmpdir.join('corrupt_scenes.txt').open() as f:
        assert product_id in f.read()

    # clean up
    tmpdir.remove()


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_invalid_id(tmpdir):
    runner = CliRunner()
    product_id = 'f30b2a6a-b0c1-49f1-INVALID-e10c3cf06101'
    command = ['--user', _api_auth[0],
        '--password', _api_auth[1],
        '--uuid', product_id,
        '--download',
        '--path', str(tmpdir)]

    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )
    assert 'No product with' in result.output
    tmpdir.remove()
