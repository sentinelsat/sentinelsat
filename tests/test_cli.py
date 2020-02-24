import json
import os
import re
import shutil
from contextlib import contextmanager
from test.support import EnvironmentVarGuard

import pytest
import requests_mock
from click.testing import CliRunner

from sentinelsat import InvalidChecksumError, SentinelAPIError, SentinelAPI
from sentinelsat.scripts.cli import cli

try:  # Python 3.5 and greater import
    from functools import partialmethod
except ImportError:  # Older versions of Python, including 2.7
    # solution taken from https://gist.github.com/carymrobbins/8940382

    from functools import partial

    class partialmethod(partial):
        def __get__(self, instance, owner):
            if instance is None:
                return self
            return partial(self.func, instance, *(self.args or ()), **(self.keywords or {}))


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

        assert_raises = pytest.raises(must_raise) if must_raise else nullcontext()
        with assert_raises:
            result = runner.invoke(
                cli,
                credential_args + list(args) if with_credentials else args,
                catch_exceptions=must_raise,
                **kwargs
            )
            if must_raise:
                raise result.exception
        if must_return_nonzero:
            assert result.exit_code != 0
        else:
            assert result.exit_code == 0
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
                    "machine scihub.copernicus.eu",
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
def test_cli(run_cli, geojson_path):
    run_cli("--geometry", geojson_path)

    run_cli("--geometry", geojson_path, "--url", "https://scihub.copernicus.eu/dhus/")

    run_cli("--geometry", geojson_path, "-q", "producttype=GRD,polarisationmode=HH")


@pytest.mark.fast
def test_no_auth_fail(run_cli, no_netrc, no_auth_environ, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://scihub.copernicus.eu/dhus/",
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
        "--url",
        "https://scihub.copernicus.eu/dhus/",
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
        "https://scihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151228",
        "-c",
        "10",
    ]

    result = run_cli("--sentinel", "2", *command)

    expected = "Product 6ed0b7de-3435-43df-98bf-ad63c8d077ef - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.47 GB"
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
        "https://scihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151228",
        "-c",
        "10",
        "--sentinel",
        "2",
        "--order-by",
        "cloudcoverpercentage,-beginposition",
    )
    assert "0848f6b8-5730-4759-850e-fc9945d42296" in result.products[1]


@pytest.mark.vcr
@pytest.mark.scihub
def test_sentinel1_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://scihub.copernicus.eu/apihub/",
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
        "https://scihub.copernicus.eu/apihub/",
        "-s",
        "20151219",
        "-e",
        "20151228",
        "--sentinel",
        "2",
    )

    expected = "Product 91c2503c-3c58-4a8c-a70b-207b128e6833 - Date: 2015-12-27T14:22:29Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 5.73 GB"
    assert expected in result.products


@pytest.mark.vcr
@pytest.mark.scihub
def test_sentinel3_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry", geojson_path, "-s", "20161201", "-e", "20161202", "--sentinel", "3"
    )

    expected = "Product 1d16f909-de53-44b0-88ad-841b0cae5cbe - Date: 2016-12-01T13:12:45.561Z, Instrument: SRAL, Mode: , Satellite: Sentinel-3, Size: 2.34 GB"
    assert expected in result.products


@pytest.mark.vcr
@pytest.mark.scihub
def test_product_flag(run_cli, geojson_path):
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://scihub.copernicus.eu/apihub/",
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

    expected = "Product 1d16f909-de53-44b0-88ad-841b0cae5cbe - Date: 2016-12-01T13:12:45.561Z, Instrument: SRAL, Mode: , Satellite: Sentinel-3, Size: 2.34 GB"
    assert expected in result.products


@pytest.mark.vcr
@pytest.mark.scihub
def test_limit_flag(run_cli, geojson_path):
    limit = 15
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://scihub.copernicus.eu/apihub/",
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
    result = run_cli("--uuid", "d8340134-878f-4891-ba4f-4df54f1e3ab4")

    expected = "Product d8340134-878f-4891-ba4f-4df54f1e3ab4 - S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A - 0.12 MB"
    assert result.products[0] == expected


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
        "S1B_IW_GRDH_1SDV_20181007T164414_20181007T164439_013049_0181B7_345E,S1B_IW_GRDH_1SDV_20181007T164349_20181007T164414_013049_0181B7_A8E3",
    )

    expected = [
        "Product b2ab53c9-abc4-4481-a9bf-1129f54c9707 - Date: 2018-10-07T16:43:49.773Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 1.65 GB",
        "Product 9e99eaa6-711e-40c3-aae5-83ea2048949d - Date: 2018-10-07T16:44:14.774Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 1.65 GB",
    ]
    assert result.products == expected


@pytest.mark.vcr
@pytest.mark.scihub
def test_name_search_empty(run_cli):
    run_cli("--name", "", must_raise=SentinelAPIError)


@pytest.mark.vcr
@pytest.mark.scihub
def test_option_hierarchy(run_cli, geojson_path):
    # expected hierarchy is producttype > instrument > platform from most to least specific
    result = run_cli(
        "--geometry",
        geojson_path,
        "--url",
        "https://scihub.copernicus.eu/apihub/",
        "-s",
        "20161201",
        "-e",
        "20161202",
        "--sentinel",
        "1",
        "--instrument",
        "SAR-C SAR",
        "--producttype",
        "S2MSI1C",
    )

    # Check that all returned products are of type 'S2MSI1C'
    assert len(result.products) > 0
    assert all("Instrument: MSI, Mode: , Satellite: Sentinel-2" in p for p in result.products)


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
        "--path",
        str(tmpdir),
        "--footprints",
    )

    assert "89 scenes found" in result.output
    gj_file = tmpdir / "search_footprints.geojson"
    assert gj_file.check()
    content = json.loads(gj_file.read_text(encoding="utf-8"))
    assert len(content["features"]) == 89
    for feature in content["features"]:
        assert len(feature["properties"]) >= 28
        coords = feature["geometry"]["coordinates"]
        assert len(coords[0]) > 3 or len(coords[0][0]) > 3
    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_single(run_cli, api, tmpdir, smallest_online_products, monkeypatch):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all",
        partialmethod(SentinelAPI.download_all, n_concurrent_dl=1, max_attempts=2),
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
    url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force the download to fail by providing an incorrect checksum
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)

        # md5 flag set (implicitly), should raise an exception
        run_cli(*command, must_raise=InvalidChecksumError)

    # clean up
    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_many(run_cli, api, tmpdir, smallest_online_products, monkeypatch):
    # Change default arguments for quicker test.
    # Also, vcrpy is not threadsafe, so only one worker is used.
    monkeypatch.setattr(
        "sentinelsat.SentinelAPI.download_all",
        partialmethod(SentinelAPI.download_all, n_concurrent_dl=1, max_attempts=2),
    )

    ids = [product["id"] for product in smallest_online_products]

    command = ["--uuid", ",".join(ids), "--download", "--path", str(tmpdir)]

    # Download 3 tiny products
    run_cli(*command)

    # Should not re-download
    run_cli(*command)

    # clean up
    for f in tmpdir.listdir():
        f.remove()

    # Prepare a response with an invalid checksum
    product_id = ids[0]
    url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % product_id
    json = api.session.get(url).json()
    json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"

    # Force one download to fail
    with requests_mock.mock(real_http=True) as rqst:
        rqst.get(url, json=json)
        # md5 flag set (implicitly), should raise an exception
        result = run_cli(*command)
        assert "is corrupted" in result.output

    assert tmpdir.join("corrupt_scenes.txt").check()
    with tmpdir.join("corrupt_scenes.txt").open() as f:
        assert product_id in f.read()

    # clean up
    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_invalid_id_cli(run_cli, tmpdir):
    product_id = "f30b2a6a-b0c1-49f1-INVALID-e10c3cf06101"
    result = run_cli(
        "--uuid", product_id, "--download", "--path", str(tmpdir), must_return_nonzero=True
    )
    assert "No product with" in result.output
    tmpdir.remove()
