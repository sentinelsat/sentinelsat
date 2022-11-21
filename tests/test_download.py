"""
Product downloading related tests.

There are two minor issues to keep in mind when recording unit tests VCRs.

1. Between calls a formerly offline product can become available, if the previous call triggered its LTA retrieval.
2. dhus and apihub have different md5 hashes for products with the same UUID.

"""
import os
import shutil

import py.path
import pytest
import requests_mock
from flaky import flaky

from sentinelsat import SentinelAPI, make_path_filter
from sentinelsat.exceptions import InvalidChecksumError, InvalidKeyError, LTAError, ServerError


@pytest.mark.fast
@pytest.mark.parametrize(
    "api_url, dhus_url",
    [
        ("https://apihub.copernicus.eu/apihub/", "https://scihub.copernicus.eu/dhus/"),
        ("https://colhub.met.no/", "https://colhub.met.no/"),
        ("https://finhub.nsdc.fmi.fi/", "https://finhub.nsdc.fmi.fi/"),
    ],
)
def test_api2dhus_url(api_url, dhus_url):
    api = SentinelAPI("mock_user", "mock_password")
    assert api._api2dhus_url(api_url) == dhus_url


@pytest.mark.mock_api
@pytest.mark.parametrize(
    "dhus_url, version",
    [
        # version numbers retrieved on January 31st, 2020
        ("https://scihub.copernicus.eu/dhus", "2.4.1"),
        ("https://colhub.met.no", "0.13.4-22"),
        ("https://finhub.nsdc.fmi.fi", "0.13.4-21-1"),
    ],
)
def test_dhus_version(dhus_url, version):
    api = SentinelAPI("mock_user", "mock_password", api_url=dhus_url)
    request_url = dhus_url + "/api/stub/version"
    with requests_mock.mock() as rqst:
        rqst.get(request_url, json={"value": version})
        assert api.dhus_version == version


@pytest.mark.mock_api
@pytest.mark.parametrize(
    "http_status_code, expected_result, headers",
    [
        # Note: the HTTP status codes have slightly more specific meanings in the LTA API.
        # OK - already online
        (200, False, {}),
        (206, False, {}),
        # Accepted for retrieval - the product offline product will be retrieved from the LTA.
        (202, True, {}),
        # already online but concurrent downloads limit was exceeded
        (
            403,
            False,
            {
                "cause-message": 'An exception occured while creating a stream: Maximum number of 4 concurrent flows achieved by the user "mock_user"'
            },
        ),
    ],
)
def test_trigger_lta_success(http_status_code, expected_result, headers):
    api = SentinelAPI("mock_user", "mock_password")
    uuid = "8df46c9e-a20c-43db-a19a-4240c2ed3b8b"

    with requests_mock.mock() as rqst:
        rqst.get(api._get_download_url(uuid), status_code=http_status_code, headers=headers)
        assert api.trigger_offline_retrieval(uuid) is expected_result


@pytest.mark.mock_api
@pytest.mark.parametrize(
    "http_status_code, exception, headers",
    [
        # Note: the HTTP status codes have slightly more specific meanings in the LTA API.
        # Forbidden - user has exceeded their offline product retrieval quota.
        (
            403,
            LTAError,
            {
                "cause-message": "User 'mock_user' offline products retrieval quota exceeded (20 fetches max) trying to fetch product S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC (143549851 bytes compressed)"
            },
        ),
        # Service Unavailable - request refused since the service is busy handling other requests.
        (503, LTAError, {}),
        # Internal Server Error - attempted to download a sub-element of an offline product.
        (500, ServerError, {}),
        (555, ServerError, {}),
        (333, ServerError, {}),
    ],
)
def test_trigger_lta_failed(http_status_code, exception, headers):
    api = SentinelAPI("mock_user", "mock_password")
    uuid = "8df46c9e-a20c-43db-a19a-4240c2ed3b8b"

    with requests_mock.mock() as rqst:
        rqst.get(api._get_download_url(uuid), status_code=http_status_code, headers=headers)
        with pytest.raises(exception):
            api.trigger_offline_retrieval(uuid)


@pytest.mark.vcr
@pytest.mark.scihub
def test_download(api, tmpdir, smallest_online_products):
    product = smallest_online_products[0]
    uuid = product["id"]
    title = product["title"]
    expected_path = tmpdir.join(title + ".zip")
    tempfile_path = tmpdir.join(title + ".zip.incomplete")

    # Download normally
    product_info = api.download(uuid, str(tmpdir), checksum=True)
    assert expected_path.samefile(product_info["path"])
    assert not tempfile_path.check(exists=1)
    assert product_info["title"] == title
    assert product_info["size"] == expected_path.size()
    assert product_info["downloaded_bytes"] == expected_path.size()

    hash = expected_path.computehash("md5")
    modification_time = expected_path.mtime()
    expected_product_info = product_info

    # File exists, expect nothing to happen
    product_info = api.download(uuid, str(tmpdir))
    assert not tempfile_path.check(exists=1)
    assert expected_path.mtime() == modification_time
    expected_product_info["downloaded_bytes"] = 0
    assert product_info == expected_product_info

    # Create invalid but full-sized tempfile, expect re-download
    expected_path.move(tempfile_path)
    with tempfile_path.open("wb") as f:
        f.seek(expected_product_info["size"] - 1)
        f.write(b"\0")
    assert tempfile_path.computehash("md5") != hash
    product_info = api.download(uuid, str(tmpdir))
    assert expected_path.check(exists=1, file=1)
    assert expected_path.computehash("md5") == hash
    expected_product_info["downloaded_bytes"] = expected_product_info["size"]
    assert product_info == expected_product_info

    # Create invalid tempfile, without checksum check
    # Expect continued download and no exception
    dummy_content = b"aaaaaaaaaaaaaaaaaaaaaaaaa"
    with tempfile_path.open("wb") as f:
        f.write(dummy_content)
    expected_path.remove()
    product_info = api.download(uuid, str(tmpdir), checksum=False)
    assert not tempfile_path.check(exists=1)
    assert expected_path.check(exists=1, file=1)
    assert expected_path.computehash("md5") != hash
    expected_product_info["downloaded_bytes"] = expected_product_info["size"] - len(dummy_content)
    assert product_info == expected_product_info

    # Create invalid tempfile, with checksum check
    # Expect continued download and exception raised
    dummy_content = b"aaaaaaaaaaaaaaaaaaaaaaaaa"
    with tempfile_path.open("wb") as f:
        f.write(dummy_content)
    expected_path.remove()
    with pytest.raises(InvalidChecksumError):
        api.download(uuid, str(tmpdir), checksum=True)
    assert not tempfile_path.check(exists=1)
    assert not expected_path.check(exists=1, file=1)

    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_all(api, tmpdir, smallest_online_products):
    ids = [product["id"] for product in smallest_online_products]

    # Download normally
    product_infos, triggered, failed_downloads = api.download_all(
        ids, str(tmpdir), max_attempts=1, n_concurrent_dl=1
    )
    assert len(failed_downloads) == 0
    assert len(triggered) == 0
    assert len(product_infos) == len(ids)
    for product_id, product_info in product_infos.items():
        pypath = py.path.local(product_info["path"])
        assert pypath.check(exists=1, file=1)
        assert pypath.purebasename in product_info["title"]
        assert pypath.size() == product_info["size"]


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_all_one_fail(api, tmpdir, smallest_online_products):
    ids = [product["id"] for product in smallest_online_products]

    # Force one download to fail
    id = ids[0]
    with requests_mock.mock(real_http=True) as rqst:
        url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % id
        json = api.session.get(url).json()
        json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"
        rqst.get(url, json=json)
        product_infos, triggered, failed_downloads = api.download_all(
            ids, str(tmpdir), max_attempts=1, n_concurrent_dl=1, checksum=True
        )
        exceptions = {k: v["exception"] for k, v in failed_downloads.items()}
        for e in exceptions.values():
            if not isinstance(e, InvalidChecksumError):
                raise e from None
        assert sorted(failed_downloads) == [ids[0]], exceptions
        assert type(list(exceptions.values())[0]) == InvalidChecksumError, exceptions
        assert triggered == {}
        assert sorted(list(product_infos) + list(failed_downloads)) == sorted(ids)
        assert id in failed_downloads

    tmpdir.remove()


# VCR.py can't handle multi-threading correctly
# https://github.com/kevin1024/vcrpy/issues/212
@flaky(max_runs=3, min_passes=2)
@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.skip
@pytest.mark.scihub
def test_download_all_lta(api, tmpdir, smallest_online_products, smallest_archived_products):
    archived_ids = [x["id"] for x in smallest_archived_products]
    online_ids = [x["id"] for x in smallest_online_products]
    ids = archived_ids[:1] + online_ids[:2]
    product_infos, triggered, failed_downloads = api.download_all(
        ids, str(tmpdir), max_attempts=1, n_concurrent_dl=1
    )
    exceptions = {k: v["exception"] for k, v in failed_downloads.items()}
    assert len(failed_downloads) == 0, exceptions
    assert len(triggered) == 1
    assert len(product_infos) == len(ids) - len(failed_downloads) - len(triggered)
    assert all(x["Online"] is False for x in triggered.values())

    # test downloaded products
    for product_id, product_info in product_infos.items():
        pypath = py.path.local(product_info["path"])
        assert pypath.check(exists=1, file=1)
        assert pypath.purebasename in product_info["title"]
        assert pypath.size() == product_info["size"]

    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_invalid_id(api):
    uuid = "1f62a176-c980-41dc-xxxx-c735d660c910"
    with pytest.raises(InvalidKeyError) as excinfo:
        api.download(uuid)
    assert "Invalid key" in str(excinfo.value)


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_quicklook(api, tmpdir, quicklook_products):
    uuid = quicklook_products[0]["id"]
    filename = quicklook_products[0]["title"]
    expected_path = tmpdir.join(filename + ".jpeg")
    # import pdb; pdb.set_trace()
    # Download normally
    quicklook_info = api.download_quicklook(uuid, str(tmpdir))
    assert expected_path.samefile(quicklook_info["path"])
    assert quicklook_info["title"] == filename
    assert quicklook_info["quicklook_size"] == expected_path.size()
    assert quicklook_info["downloaded_bytes"] == expected_path.size()

    modification_time = expected_path.mtime()
    expected_quicklook_info = quicklook_info

    # File exists, expect nothing to happen
    quicklook_info = api.download_quicklook(uuid, str(tmpdir))
    assert expected_path.mtime() == modification_time
    expected_quicklook_info["downloaded_bytes"] = 0
    assert quicklook_info["quicklook_size"] == expected_path.size()
    assert quicklook_info == expected_quicklook_info

    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_all_quicklooks(api, tmpdir, quicklook_products):
    ids = [product["id"] for product in quicklook_products]

    # Download normally
    downloaded_quicklooks, failed_quicklooks = api.download_all_quicklooks(
        ids, str(tmpdir), n_concurrent_dl=1
    )
    assert len(failed_quicklooks) == 0
    assert len(downloaded_quicklooks) == len(ids)
    for product_id, product_info in downloaded_quicklooks.items():
        pypath = py.path.local(product_info["path"])
        assert pypath.check(exists=1, file=1)
        assert pypath.purebasename in product_info["title"]
        assert pypath.size() == product_info["quicklook_size"]

    tmpdir.remove()


@pytest.mark.vcr(allow_playback_repeats=True)
@pytest.mark.scihub
def test_download_all_quicklooks_one_fail(api, tmpdir, quicklook_products):
    ids = [product["id"] for product in quicklook_products]

    # Force one download to fail
    id = ids[0]
    with requests_mock.mock(real_http=True) as rqst:
        url = f"https://apihub.copernicus.eu/apihub/odata/v1/Products('{id}')/Products('Quicklook')/$value"
        headers = api.session.get(url).headers
        headers["content-type"] = "image/xxxx"
        rqst.get(url, headers=headers)
        downloaded_quicklooks, failed_quicklooks = api.download_all_quicklooks(
            ids, str(tmpdir), n_concurrent_dl=1
        )
        assert len(failed_quicklooks) == 1
        assert len(downloaded_quicklooks) + len(failed_quicklooks) == len(ids)
        assert id in failed_quicklooks

    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_quicklook_invalid_id(api):
    uuid = "1f62a176-c980-41dc-xxxx-c735d660c910"
    with pytest.raises(InvalidKeyError) as excinfo:
        api.download_quicklook(uuid)
    assert "Invalid key" in str(excinfo.value)


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_stream(api, tmpdir, smallest_online_products):
    product_info = smallest_online_products[0]
    uuid = product_info["id"]
    filename = product_info["title"]
    expected_path = tmpdir.join(filename + ".zip")

    response = api.get_stream(uuid)
    assert product_info["title"] == filename
    with open(expected_path, "wb") as f:
        shutil.copyfileobj(response.raw, f)

    assert product_info["size"] == expected_path.size()
    assert api._checksum_compare(expected_path, product_info)

    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_product_nodes(api, tmpdir, node_test_products):
    uuid = node_test_products[0]["id"]
    product_dir = node_test_products[0]["title"] + ".SAFE"
    expected_path = tmpdir.join(product_dir)

    nodefilter = make_path_filter("*preview/*.kml")
    product_info = api.download(uuid, str(tmpdir), checksum=True, nodefilter=nodefilter)

    assert os.path.normpath(product_info["node_path"]) == product_dir
    assert expected_path.exists()

    assert set(product_info["nodes"]) == {"./manifest.safe", "preview/map-overlay.kml"}

    assert tmpdir.join(product_dir, "manifest.safe").check()
    assert tmpdir.join(product_dir, "preview", "map-overlay.kml").check()

    assert not tmpdir.join(product_dir, "manifest.safe" + ".incomplete").check()
    assert not tmpdir.join(product_dir, "preview", "map-overlay.kml" + ".incomplete").check()

    tmpdir.remove()
