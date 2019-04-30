import py.path
import pytest
import requests_mock

from sentinelsat import SentinelAPI, SentinelAPILTAError, InvalidChecksumError, SentinelAPIError


@pytest.mark.mock_api
def test_trigger_lta_accepted():
    api = SentinelAPI("mock_user", "mock_password")

    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value"

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url,
            text="Mock trigger accepted", status_code=202
        )
        assert api._trigger_offline_retrieval(request_url) == 202


@pytest.mark.mock_api
@pytest.mark.parametrize("http_status_code", [
    503,  # service unavailable
    403,  # user quota exceeded
    500,  # internal server error
])
def test_trigger_lta_failed(http_status_code):
    api = SentinelAPI("mock_user", "mock_password")
    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value"

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url,
            status_code=http_status_code
        )
        with pytest.raises(SentinelAPILTAError) as excinfo:
            api._trigger_offline_retrieval(request_url)


@pytest.mark.vcr
@pytest.mark.scihub
def test_download(api, tmpdir, smallest_online_products):
    uuid = smallest_online_products[0]['id']
    filename = smallest_online_products[0]['title']
    expected_path = tmpdir.join(filename + ".zip")
    tempfile_path = tmpdir.join(filename + ".zip.incomplete")

    # Download normally
    product_info = api.download(uuid, str(tmpdir), checksum=True)
    assert expected_path.samefile(product_info["path"])
    assert not tempfile_path.check(exists=1)
    assert product_info["title"] == filename
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
        f.write(b'\0')
    assert tempfile_path.computehash("md5") != hash
    product_info = api.download(uuid, str(tmpdir))
    assert expected_path.check(exists=1, file=1)
    assert expected_path.computehash("md5") == hash
    expected_product_info["downloaded_bytes"] = expected_product_info["size"]
    assert product_info == expected_product_info

    # Create invalid tempfile, without checksum check
    # Expect continued download and no exception
    dummy_content = b'aaaaaaaaaaaaaaaaaaaaaaaaa'
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
    dummy_content = b'aaaaaaaaaaaaaaaaaaaaaaaaa'
    with tempfile_path.open("wb") as f:
        f.write(dummy_content)
    expected_path.remove()
    with pytest.raises(InvalidChecksumError):
        api.download(uuid, str(tmpdir), checksum=True)
    assert not tempfile_path.check(exists=1)
    assert not expected_path.check(exists=1, file=1)

    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_all(api, tmpdir, smallest_online_products):
    ids = [product['id'] for product in smallest_online_products]

    # Download normally
    product_infos, triggered, failed_downloads = api.download_all(ids, str(tmpdir))
    assert len(failed_downloads) == 0
    assert len(triggered) == 0
    assert len(product_infos) == len(ids)
    for product_id, product_info in product_infos.items():
        pypath = py.path.local(product_info['path'])
        assert pypath.check(exists=1, file=1)
        assert pypath.purebasename in product_info['title']
        assert pypath.size() == product_info["size"]

    # Force one download to fail
    id, product_info = list(product_infos.items())[0]
    path = product_info['path']
    py.path.local(path).remove()
    with requests_mock.mock(real_http=True) as rqst:
        url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')?$format=json" % id
        json = api.session.get(url).json()
        json["d"]["Checksum"]["Value"] = "00000000000000000000000000000000"
        rqst.get(url, json=json)
        product_infos, triggered, failed_downloads = api.download_all(
            ids, str(tmpdir), max_attempts=1, checksum=True)
        assert len(failed_downloads) == 1
        assert len(product_infos) + len(failed_downloads) == len(ids)
        assert id in failed_downloads

    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_all_lta(api, tmpdir, smallest_archived_products):
    ids = [product['id'] for product in smallest_archived_products]

    product_infos, triggered, failed_downloads = api.download_all(ids, str(tmpdir))
    assert len(failed_downloads) == 0
    assert len(triggered) == 3
    assert len(product_infos) == len(ids) - len(failed_downloads) - len(triggered)
    assert all(x['Online'] is False for x in triggered.values())

    # test downloaded products
    for product_id, product_info in product_infos.items():
        pypath = py.path.local(product_info['path'])
        assert pypath.check(exists=1, file=1)
        assert pypath.purebasename in product_info['title']
        assert pypath.size() == product_info["size"]

    tmpdir.remove()


@pytest.mark.vcr
@pytest.mark.scihub
def test_download_invalid_id(api):
    uuid = "1f62a176-c980-41dc-xxxx-c735d660c910"
    with pytest.raises(SentinelAPIError) as excinfo:
        api.download(uuid)
    assert 'Invalid key' in excinfo.value.msg
