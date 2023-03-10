import json
import os
import re
import glob
import shutil
from contextlib import contextmanager
from functools import partialmethod

try:
    from test.support.os_helper import EnvironmentVarGuard
except ImportError:
    from test.support import EnvironmentVarGuard

import pytest
import requests_mock
from click.testing import CliRunner

from sentinelsat import SentinelAPI, InvalidChecksumError
from sentinelsat.scripts.cli import cli


@pytest.fixture(scope="session")
def run_cli(credentials):
    runner = CliRunner()
    credential_args = ["--user", credentials[0] or "", "--password", credentials[1] or ""]

    @contextmanager
    def nullcontext():
        yield

    def run(*args, **kwargs):
        """Runs the sentinelsat CLI

        Parameters
        ----------
        *args : str
            The command-line arguments
        with_credentials : bool, optional
            Whether the credentials from DHUS_* environment variables are passed to the CLI
            as --user and --password parameters. Defaults to True.
        must_return_nonzero : bool, optiona
            Asserts that the program returns a non-zero (failure) exit code.
            A zero (success) exit code is asserted otherwise. Defaults to false.
        must_raise : Exception, optional
            If an exception type is provided asserts that a exception of this type is raised.
            Implies must_return_nonzero=True.
        **kwargs
            Any remaining keyword arguments are passed directly to CliRunner.invoke().

        Returns
        -------
            The click.testing.Result object returned by CliRunner.invoke().
            Includes an additional products attribute with a list of products printed
            to stdout by the program.
        """
        with_credentials = kwargs.pop("with_credentials", True)
        must_raise = kwargs.pop("must_raise", None)
        must_return_nonzero = kwargs.pop("must_return_nonzero", False) or must_raise is not None

        # Otherwise tqdm.write() messes up the stdout for testing
        os.environ["DISABLE_TQDM_LOGGING"] = "y"

        assert_raises = pytest.raises(must_raise) if must_raise else nullcontext()
        with assert_raises:
            result = runner.invoke(
                cli,
                credential_args + list(args) if with_credentials else args,
                catch_exceptions=must_raise,
                **kwargs
            )
            if must_raise:
                assert result.exception is not None, result.output
                raise result.exception
        if must_return_nonzero:
            assert result.exit_code != 0, result.output
        else:
            assert result.exit_code == 0, result.output
        result.products = re.findall("^Product .+$", result.output, re.M)
        return result

    return run


@pytest.fixture
def no_auth_environ():
    with EnvironmentVarGuard() as guard:
        # Temporarily unset credential environment variables
        guard.unset("DHUS_USER")
        guard.unset("DHUS_PASSWORD")
        yield


@pytest.fixture
def no_netrc():
    netrcpath = os.path.expanduser("~/.netrc")
    netrcpath_bak = netrcpath + ".bak"
    if os.path.isfile(netrcpath):
        shutil.move(netrcpath, netrcpath_bak)
        try:
            yield
        finally:
            shutil.move(netrcpath_bak, netrcpath)
    else:
        yield


@pytest.fixture
def netrc_from_environ(no_netrc, credentials):
    netrcpath = os.path.expanduser("~/.netrc")
    assert not os.path.exists(netrcpath)
    with open(netrcpath, "w") as f:
        f.write(
            "\n".join(
                [
                    "machine apihub.copernicus.eu",
                    "login {}".format(credentials[0]),
                    "password {}".format(credentials[1]),
                ]
            )
        )
    try:
        yield
    finally:
        os.remove(netrcpath)


@pytest.mark.vcr
@pytest.mark.scihub
def test_cli_gnss(run_cli):
    run_cli(
        "--gnss",
        "-s",
        "20210201",
        "-e",
        "20210202",
        "--producttype",
        "AUX_POEORB",
        "--query",
        "platformserialidentifier=1B",
    )


@pytest.mark.vcr
@pytest.mark.scihub
def test_cli_geometry_alternatives(run_cli, geojson_string, wkt_string):
    run_cli("--geometry", geojson_string, "--end", "20200101", "--limit", "1")
    run_cli("--geometry", wkt_string, "--end", "20200101", "--limit", "1")


@pytest.mark.fast
def test_cli_geometry_WKT_alternative_fail(run_cli):
    result = run_cli(
        "--geometry",
        "POLYGO((-87.27 41.64,-81.56 37.857,-82.617 44.52,-87.2 41.64))",
        "--end",
        "20200101",
        "--limit",
        "1",
        must_return_nonzero=True,
    )
    assert (
        "neither a GeoJSON file with a valid path, a GeoJSON String nor a WKT string."
        in result.output
    )


@pytest.mark.fast
def test_cli_geometry_JSON_alternative_fail(run_cli):
    result = run_cli(
        "--geometry",
        '{"type": "A bad JSON", "features" :[nothing], ([{ ',
        "--end",
        "20200101",
        "--limit",
        "1",
        must_return_nonzero=True,
    )
    assert "geometry string starts with '{' but is not a valid GeoJSON." in result.output


@pytest.mark.fast
def test_no_auth_fail(run_cli, no_netrc, no_auth_environ, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--end",
        "20200101",
        "--limit",
        "1",
        with_credentials=False,
        must_return_nonzero=True,
    )
    assert "--user" in result.output


@pytest.mark.vcr
@pytest.mark.scihub
def test_no_auth_netrc(run_cli, netrc_from_environ, no_auth_environ, geojson_path):
    run_cli(
        "--geometry",
        geojson_path,
        "--end",
        "20200101",
        "--limit",
        "1",
        with_credentials=False,
    )


@pytest.mark.vcr
@pytest.mark.scihub
def test_returned_filesize(run_cli, geojson_path):
    result = run_cli(
        "--geometry", geojson_path, "-s", "20141205", "-e", "20141208", "-q", "producttype=GRD"
    )
    expected = "1 scenes found with a total size of 0.50 GB"
    assert result.output.split("\n")[-2] == expected

    result = run_cli(
        "--geometry", geojson_path, "-s", "20170101", "-e", "20170105", "-q", "producttype=GRD"
    )
    expected = "18 scenes found with a total size of 27.81 GB"
    assert result.output.split("\n")[-2] == expected


@pytest.mark.vcr
@pytest.mark.scihub
def test_cloud_flag_url(run_cli, geojson_path):
    command = [
        "--geometry",
        geojson_path,
        "--url",
        "https://apihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151220",
        "-c",
        "10",
    ]

    result = run_cli("--sentinel", "2", *command)

    expected = "Product e071bdda-47ec-4434-aafa-00340442bdda - Date: 2015-12-19T14:47:22.029Z, Instrument: MSI, Satellite: Sentinel-2, Size: 403.60 MB"
    assert result.products[0] == expected
    # For order-by test
    assert "0848f6b8-5730-4759-850e-fc9945d42296" not in result.products[1]

    run_cli("--sentinel", "1", *command, must_return_nonzero=True)


@pytest.mark.vcr
@pytest.mark.scihub
def test_order_by_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://apihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151220",
        "--order-by",
        "platformname,-size",
    )
    # Check that order matches platformname,-size
    sats = []
    sizes = {}
    for prod in result.products:
        m = re.search(r"Satellite: (\S+), Size: (\S+ \S+)", prod)
        assert m, prod
        sats.append(m.group(1))
        sizes.setdefault(m.group(1), []).append(m.group(2))
    assert sats == sorted(sats)
    for sizes_group in sizes.values():
        assert sizes_group == sorted(sizes_group, reverse=True)


@pytest.mark.vcr
@pytest.mark.scihub
def test_sentinel1_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://apihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151228",
        "--sentinel",
        "1",
    )

    expected = "Product 6a62313b-3d6f-489e-bfab-71ce8d7f57db - Date: 2015-12-24T09:40:34.129Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.7 GB"
    assert expected in result.products


@pytest.mark.vcr
@pytest.mark.scihub
def test_sentinel2_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://apihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151228",
        "--sentinel",
        "2",
        "--limit",
        "5",
    )
    for prod in result.products:
        assert "Satellite: Sentinel-2" in prod


@pytest.mark.vcr
@pytest.mark.scihub
def test_sentinel3_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "-s",
        "20161201",
        "-e",
        "20161202",
        "--sentinel",
        "3",
        "--limit",
        "5",
    )
    for prod in result.products:
        assert "Satellite: Sentinel-3" in prod


@pytest.mark.vcr
@pytest.mark.scihub
def test_product_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://apihub.copernicus.eu/apihub/",
        "-s",
        "20161201",
        "-e",
        "20161202",
        "--producttype",
        "SLC",
    )

    expected = "Product 2223103a-3754-473d-9a29-24ef8efa2880 - Date: 2016-12-01T09:30:22.149Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.98 GB"
    assert result.products[3] == expected


@pytest.mark.vcr
@pytest.mark.scihub
def test_instrument_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry", geojson_path, "-s", "20161201", "-e", "20161202", "--instrument", "SRAL"
    )
    for prod in result.products:
        assert "Instrument: SRAL" in prod
        assert "Date: 2016-12-01" in prod or "Date: 2016-12-02" in prod


@pytest.mark.vcr
@pytest.mark.scihub
def test_limit_flag(run_cli, geojson_path):
    limit = 15
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://apihub.copernicus.eu/apihub/",
        "-s",
        "20161201",
        "-e",
        "20161230",
        "--limit",
        str(limit),
    )

    assert len(result.products) == limit


@pytest.mark.vcr
@pytest.mark.scihub
def test_uuid_search(run_cli):
    uuid = "d8340134-878f-4891-ba4f-4df54f1e3ab4"
    result = run_cli("--uuid", uuid)
    assert len(result.products) == 1
    assert uuid in result.products[0]


@pytest.mark.vcr
@pytest.mark.scihub
def test_name_search(run_cli):
    result = run_cli(
        "--name", "S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A"
    )

    expected = "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - Date: 2015-05-26T21:10:28.984Z, Instrument: SAR-C SAR, Mode: VV, Satellite: Sentinel-1, Size: 10.65 KB"
    assert result.products[0] == expected


@pytest.mark.vcr
@pytest.mark.scihub
def test_name_search_multiple(run_cli):
    result = run_cli(
        "--name",
        "S1B_IW_GRDH_1SDV_20181007T164414_20181007T164439_013049_0181B7_345E",
        "--name",
        "S1B_IW_GRDH_1SDV_20181007T164349_20181007T164414_013049_0181B7_A8E3",
        "-q",
        "identifier=S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A",
        "-q",
        "identifier=S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A",
        "-q",
        "identifier=S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E",
    )

    expected = {
        "Product b2ab53c9-abc4-4481-a9bf-1129f54c9707 - Date: 2018-10-07T16:43:49.773Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 1.65 GB",
        "Product 9e99eaa6-711e-40c3-aae5-83ea2048949d - Date: 2018-10-07T16:44:14.774Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 1.65 GB",
        "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - Date: 2015-05-26T21:10:28.984Z, Instrument: SAR-C SAR, Mode: VV, Satellite: Sentinel-1, Size: 10.65 KB",
        "Product 1f62a176-c980-41dc-b3a1-c735d660c910 - Date: 2015-06-03T09:26:24.921Z, Instrument: SAR-C SAR, Mode: HH, Satellite: Sentinel-1, Size: 10.54 KB",
    }
    assert set(result.products) == expected


@pytest.mark.vcr
@pytest.mark.scihub
def test_repeated_keywords(run_cli):
    uuids = ["d8340134-878f-4891-ba4f-4df54f1e3ab4", "1f62a176-c980-41dc-b3a1-c735d660c910"]
    result = run_cli("-q", "uuid=" + uuids[0], "-q", "uuid=" + uuids[1])
    result_uuids = set(prod.split(" ", 2)[1] for prod in result.products)
    assert result_uuids == set(uuids)


@pytest.mark.vcr
@pytest.mark.scihub
def test_name_search_empty(run_cli):
    run_cli("--name", "", must_raise=ValueError)


@pytest.mark.vcr
@pytest.mark.scihub
def test_footprints_cli(run_cli, tmpdir, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "-s",
        "20151219",
        "-e",
        "20151228",
        "--sentinel",
        "2",
        "--footprints",
        str(tmpdir / "test.geojson"),
    )
    assert len(result.products) == 89
    gj_file = tmpdir / "test.geojson"
    assert gj_file.check()
    content = json.loads(gj_file.read_text(encoding="utf-8"))
    assert len(content["features"]) == len(result.products)
    for feature in content["features"]:
        assert len(feature["properties"]) >= 28
        coords = feature["geometry"]["coordinates"]
        assert len(coords[0]) > 3 or len(coords[0][0]) > 3


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_single(run_cli, api, tmpdir, smallest_online_products, monkeypatch):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all",
        partialmethod(SentinelAPI.download_all, max_attempts=2, n_concurrent_dl=1),
    )

    product_id = smallest_online_products[0]["id"]
    command = ["--uuid", product_id, "--download", "--path", str(tmpdir)]

    run_cli(*command)

    # The file already exists, should not be re-downloaded
    run_cli(*command)

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force the download to fail by providing an incorrect checksum
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)

        # md5 flag set (implicitly), should raise an exception
        run_cli(*command, "--fail-fast", must_raise=InvalidChecksumError)

        # md5 flag set (implicitly), should raise an exception
        result = run_cli(*command, must_return_nonzero=True)
        assert "is corrupted" in result.output

    # clean up
    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_product_node_download_single(run_cli, api, tmpdir, smallest_online_products, monkeypatch):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all",
        partialmethod(SentinelAPI.download_all, max_attempts=2, n_concurrent_dl=1),
    )
    product_id = smallest_online_products[0]["id"]
    command = ["--uuid", product_id, "--download", "--path", str(tmpdir)]

    run_cli(*command)

    # The file already exists, should not be re-downloaded
    run_cli(*command)

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force the download to fail by providing an incorrect checksum
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)

        # md5 flag set (implicitly), should raise an exception
        result = run_cli(*command, must_return_nonzero=True)
        assert "is corrupted" in result.output

    # clean up
    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_product_node_download_single_with_filter(
    run_cli, api, tmpdir, node_test_products, monkeypatch
):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all",
        partialmethod(SentinelAPI.download_all, max_attempts=2, n_concurrent_dl=1),
    )

    product_id = node_test_products[0]["id"]
    command = [
        "--uuid",
        product_id,
        "--download",
        "--path",
        str(tmpdir),
        "--include-pattern",
        "*.kml",
    ]

    run_cli(*command)

    # The file already exists, should not be re-downloaded
    run_cli(*command)

    files = list(glob.glob(str(tmpdir.join("S*.SAFE", "*"))))
    assert len(files) == 2
    basenames = [os.path.basename(filename) for filename in files]
    assert "manifest.safe" in basenames
    assert "preview" in basenames

    files = list(glob.glob(str(tmpdir.join("S*.SAFE", "preview", "*"))))
    assert len(files) == 1
    basenames = [os.path.basename(filename) for filename in files]
    assert "map-overlay.kml" in basenames

    # clean up
    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_many(run_cli, api, tmpdir, smallest_online_products, monkeypatch):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all",
        partialmethod(SentinelAPI.download_all, max_attempts=2, n_concurrent_dl=1),
    )

    ids = sorted(product["id"] for product in smallest_online_products)

    command = ["--download", "--path", str(tmpdir)]
    for id in ids:
        command += ["--uuid", id]

    # Download 3 tiny products
    run_cli(*command)

    # Should not re-download
    run_cli(*command)

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    product_id = ids[0]
    url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force one download to fail
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)
        # md5 flag set (implicitly), should raise an exception
        result = run_cli(*command, must_return_nonzero=True)
        assert "is corrupted" in result.output

    assert tmpdir.join("corrupt_scenes.txt").check()
    with tmpdir.join("corrupt_scenes.txt").open() as f:
        assert product_id in f.read()

    # clean up
    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_single_quicklook(run_cli, api, tmpdir, quicklook_products, monkeypatch):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all_quicklooks",
        partialmethod(SentinelAPI.download_all_quicklooks, n_concurrent_dl=1),
    )

    id = quicklook_products[0]["id"]
    command = ["--uuid", id, "--quicklook", "--path", str(tmpdir)]

    run_cli(*command)

    # The file already exists, should not be re-downloaded
    run_cli(*command)

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('{id}')/Products('Quicklook')/$value".format(
        id=id
    )
    headers = api.session.get(url).headers
    headers["content-type"] = "image/xxxx"

    # Force the download to fail by providing an incorrect content type
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, headers=headers)

        # incorrect content-type, should fail
        result = run_cli(*command)
        assert "Some quicklooks failed: 1" in result.output

    # clean up
    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_info_cli(run_cli):
    result = run_cli("--info")
    assert result.output == (
        "HTTPError: 404 Client Error: Not Found for url: https://apihub.copernicus.eu/apihub/api/stub/version\n"
        "Are you trying to get the DHuS version of APIHub?\nTrying again after conversion to DHuS URL\n"
        "DHuS version: 2.4.1\n"
    )


@pytest.mark.vcr
@pytest.mark.scihub
def test_location_cli(run_cli):
    result = run_cli("--location", "Metz", "-s" "20200101", "-e" "20200102", "-l", "1")
    assert "Found" in result.output
    m = re.search(r"Found (\d+) products", result.output)
    assert m, result.output
    assert int(m.group(1)) < 100
