import os
import re
import json
import shutil
import contextlib

import pytest
import requests_mock
from click.testing import CliRunner

from sentinelsat import InvalidChecksumError, SentinelAPIError, SentinelAPI
from sentinelsat.scripts.cli import cli
from .shared import my_vcr, FIXTURES_DIR

# local tests require environment variables `DHUS_USER` and `DHUS_PASSWORD`
# for Travis CI they are set as encrypted environment variables and stored
AUTH_VARS = ['DHUS_USER', 'DHUS_PASSWORD']
API_AUTH = [os.environ.get(name, None) for name in AUTH_VARS]

# TODO: change test fixtures from subcommands to unified commands


@contextlib.contextmanager
def no_auth_environ():
    old_environ = {name: os.environ.pop(name, None) for name in AUTH_VARS}
    try:
        yield
    finally:
        # restore old values
        for name, value in old_environ.items():
            if value is not None:
                os.environ[name] = value


@contextlib.contextmanager
def no_netrc():
    netrcpath = os.path.expanduser('~/.netrc')
    netrcpath_bak = netrcpath + '.bak'
    if os.path.isfile(netrcpath):
        shutil.move(netrcpath, netrcpath_bak)
        try:
            yield
        finally:
            shutil.move(netrcpath_bak, netrcpath)


@contextlib.contextmanager
def netrc_from_environ():
    netrcpath = os.path.expanduser('~/.netrc')
    with no_netrc():
        with open(netrcpath, 'w') as f:
            f.write('\n'.join([
                'machine scihub.copernicus.eu',
                'login {}'.format(API_AUTH[0]),
                'password {}'.format(API_AUTH[1])
            ]))
        yield
        os.remove(netrcpath)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_cli(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path],
        catch_exceptions=False
    )

    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/dhus/'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '-q', 'producttype=GRD,polarisationmode=HH'],
        catch_exceptions=False
    )
    assert result.exit_code == 0


def test_no_auth_fail(geojson_path):
    with no_netrc():
        with no_auth_environ():
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ['--geometry', geojson_path,
                 '--url', 'https://scihub.copernicus.eu/dhus/'],
                catch_exceptions=False
            )
            assert result.exit_code != 0
            assert '--user' in result.output


@my_vcr.use_cassette
@pytest.mark.scihub
def test_no_auth_netrc(geojson_path):
    with netrc_from_environ():
        with no_auth_environ():
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ['--geometry', geojson_path,
                 '--url', 'https://scihub.copernicus.eu/dhus/'],
                catch_exceptions=False
            )
            print(result.output)
            assert result.exit_code == 0


@my_vcr.use_cassette
@pytest.mark.scihub
def test_returned_filesize(geojson_path):
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '-s', '20141205',
         '-e', '20141208',
         '-q', 'producttype=GRD'],
        catch_exceptions=False
    )
    assert result.exit_code == 0
    expected = "1 scenes found with a total size of 0.50 GB"
    assert result.output.split("\n")[-2] == expected

    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '-s', '20170101',
         '-e', '20170105',
         '-q', 'producttype=GRD'],
        catch_exceptions=False
    )
    assert result.exit_code == 0
    expected = "18 scenes found with a total size of 27.81 GB"
    assert result.output.split("\n")[-2] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_cloud_flag_url(geojson_path):
    command = ['--user', API_AUTH[0],
               '--password', API_AUTH[1],
               '--geometry', geojson_path,
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
    assert result.exit_code == 0

    expected = "Product 6ed0b7de-3435-43df-98bf-ad63c8d077ef - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.47 GB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected
    # For order-by test
    assert '0848f6b8-5730-4759-850e-fc9945d42296' not in re.findall("^Product .+$", result.output, re.M)[1]

    result = runner.invoke(
        cli,
        command + ['--sentinel', '1'],
        catch_exceptions=False
    )
    assert result.exit_code != 0


@my_vcr.use_cassette
@pytest.mark.scihub
def test_order_by_flag(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '-c', '10',
         '--sentinel', '2',
         '--order-by', 'cloudcoverpercentage,-beginposition'],
        catch_exceptions=False
    )
    assert result.exit_code == 0
    assert '0848f6b8-5730-4759-850e-fc9945d42296' in re.findall("^Product .+$", result.output, re.M)[1]


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel1_flag(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel', '1'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product 6a62313b-3d6f-489e-bfab-71ce8d7f57db - Date: 2015-12-24T09:40:34.129Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.7 GB"
    assert expected in re.findall("^Product .+$", result.output, re.M)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel2_flag(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel', '2'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product 91c2503c-3c58-4a8c-a70b-207b128e6833 - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.73 GB"
    assert expected in re.findall("^Product .+$", result.output, re.M)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_sentinel3_flag(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '-s', '20161201',
         '-e', '20161202',
         '--sentinel', '3'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product 1d16f909-de53-44b0-88ad-841b0cae5cbe - Date: 2016-12-01T13:12:45.561Z, Instrument: SRAL, Mode: , Satellite: Sentinel-3, Size: 2.34 GB"
    assert expected in re.findall("^Product .+$", result.output, re.M)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_product_flag(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20161201',
         '-e', '20161202',
         '--producttype', 'SLC'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product 2223103a-3754-473d-9a29-24ef8efa2880 - Date: 2016-12-01T09:30:22.149Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.98 GB"
    assert re.findall("^Product .+$", result.output, re.M)[3] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_instrument_flag(geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '-s', '20161201',
         '-e', '20161202',
         '--instrument', 'SRAL'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product 1d16f909-de53-44b0-88ad-841b0cae5cbe - Date: 2016-12-01T13:12:45.561Z, Instrument: SRAL, Mode: , Satellite: Sentinel-3, Size: 2.34 GB"
    assert expected in re.findall("^Product .+$", result.output, re.M)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_limit_flag(geojson_path):
    runner = CliRunner()
    limit = 15
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20161201',
         '-e', '20161230',
         '--limit', str(limit)],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    num_products = len(re.findall("^Product ", result.output, re.MULTILINE))
    assert num_products == limit


@my_vcr.use_cassette
@pytest.mark.scihub
def test_uuid_search():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--uuid', 'd8340134-878f-4891-ba4f-4df54f1e3ab4'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A - 0.12 MB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_name_search():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--name', 'S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - Date: 2015-05-26T21:10:28.984Z, Instrument: SAR-C SAR, Mode: VV, Satellite: Sentinel-1, Size: 10.65 KB"
    assert re.findall("^Product .+$", result.output, re.M)[0] == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_name_search_multiple():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--name', 'S1B_IW_GRDH_1SDV_20181007T164414_20181007T164439_013049_0181B7_345E,S1B_IW_GRDH_1SDV_20181007T164349_20181007T164414_013049_0181B7_A8E3'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    expected = [
        'Product b2ab53c9-abc4-4481-a9bf-1129f54c9707 - Date: 2018-10-07T16:43:49.773Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 1.65 GB',
        'Product 9e99eaa6-711e-40c3-aae5-83ea2048949d - Date: 2018-10-07T16:44:14.774Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 1.65 GB'
    ]
    assert re.findall("^Product .+$", result.output, re.M) == expected


@my_vcr.use_cassette
@pytest.mark.scihub
def test_name_search_empty():
    runner = CliRunner()
    with pytest.raises(SentinelAPIError):
        result = runner.invoke(
            cli,
            ['--user', API_AUTH[0],
             '--password', API_AUTH[1],
             '--name', ''],
            catch_exceptions=True
        )
        assert result.exit_code != 0
        raise result.exception


@my_vcr.use_cassette
@pytest.mark.scihub
def test_option_hierarchy(geojson_path):
    # expected hierarchy is producttype > instrument > platform from most to least specific
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '--url', 'https://scihub.copernicus.eu/apihub/',
         '-s', '20161201',
         '-e', '20161202',
         '--sentinel', '1',
         '--instrument', 'SAR-C SAR',
         '--producttype', 'S2MSI1C'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    products = re.findall("^Product .+$", result.output, re.M)
    # Check that all returned products are of type 'S2MSI1C'
    assert len(products) > 0
    assert all("Instrument: MSI, Mode: , Satellite: Sentinel-2" in p for p in products)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_footprints_cli(tmpdir, geojson_path):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['--user', API_AUTH[0],
         '--password', API_AUTH[1],
         '--geometry', geojson_path,
         '-s', '20151219',
         '-e', '20151228',
         '--sentinel', '2',
         '--path', str(tmpdir),
         '--footprints'],
        catch_exceptions=False
    )
    assert result.exit_code == 0

    assert '11 scenes found' in result.output
    gj_file = tmpdir / 'search_footprints.geojson'
    assert gj_file.check()
    content = json.loads(gj_file.read_text(encoding='utf-8'))
    assert len(content['features']) == 11
    for feature in content['features']:
        assert len(feature['properties']) >= 28
        assert len(feature['geometry']['coordinates'][0]) > 3
    tmpdir.remove()


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_single(tmpdir):
    runner = CliRunner()

    product_id = '5618ce1b-923b-4df2-81d9-50b53e5aded9'
    command = ['--user', API_AUTH[0],
               '--password', API_AUTH[1],
               '--uuid', product_id,
               '--download',
               '--path', str(tmpdir)]
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )
    assert result.exit_code == 0

    # The file already exists, should not be re-downloaded
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )
    assert result.exit_code == 0

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    api = SentinelAPI(*API_AUTH)
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force the download to fail by providing an incorrect checksum
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)

        # md5 flag set (implicitly), should raise an exception
        with pytest.raises(InvalidChecksumError):
            result = runner.invoke(
                cli,
                command,
                catch_exceptions=True
            )
            assert result.exit_code != 0
            raise result.exception

    # clean up
    tmpdir.remove()


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_many(tmpdir):
    runner = CliRunner()

    command = ['--user', API_AUTH[0],
               '--password', API_AUTH[1],
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
    assert result.exit_code == 0

    # Should not re-download
    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )
    assert result.exit_code == 0

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    product_id = 'd8340134-878f-4891-ba4f-4df54f1e3ab4'
    url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    api = SentinelAPI(*API_AUTH)
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
        assert result.exit_code == 0
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
    command = ['--user', API_AUTH[0],
               '--password', API_AUTH[1],
               '--uuid', product_id,
               '--download',
               '--path', str(tmpdir)]

    result = runner.invoke(
        cli,
        command,
        catch_exceptions=False
    )
    assert result.exit_code != 0
    assert 'No product with' in result.output
    tmpdir.remove()
