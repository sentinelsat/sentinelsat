# -*- coding: utf-8 -*-
import hashlib

import pytest
import requests
import requests_mock

from sentinelsat import SentinelAPI, SentinelAPIError
from sentinelsat.sentinel import _parse_opensearch_response


@pytest.mark.fast
def test_checksumming_progressbars(capsys, fixture_path):
    api = SentinelAPI("mock_user", "mock_password")
    testfile_md5 = hashlib.md5()
    true_path = fixture_path("expected_search_footprints_s1.geojson")
    with open(true_path, "rb") as testfile:
        testfile_md5.update(testfile.read())
        real_md5 = testfile_md5.hexdigest()

    assert api._md5_compare(true_path, real_md5) is True
    out, err = capsys.readouterr()
    assert "checksumming" in err
    api = SentinelAPI("mock_user", "mock_password", show_progressbars=False)
    assert api._md5_compare(fixture_path("map.geojson"), real_md5) is False
    out, err = capsys.readouterr()
    assert out == ""
    assert "checksumming" not in err


@pytest.mark.vcr
# Relevant pull request: https://github.com/kevin1024/vcrpy/pull/386
@pytest.mark.skip(reason="Cannot mock since VCR.py has issues with Unicode request bodies.")
@pytest.mark.scihub
def test_unicode_support(api):
    test_str = "٩(●̮̮̃•̃)۶:"

    with pytest.raises(SentinelAPIError) as excinfo:
        api.count(raw=test_str)
    assert test_str == excinfo.value.response.json()["feed"]["opensearch:Query"]["searchTerms"]

    with pytest.raises(SentinelAPIError) as excinfo:
        api.get_product_odata(test_str)
    assert test_str in excinfo.value.response.json()["error"]["message"]["value"]


@pytest.mark.mock_api
def test_scihub_unresponsive(small_query):
    timeout_connect = 6
    timeout_read = 6.6
    timeout = (timeout_connect, timeout_read)

    api = SentinelAPI("mock_user", "mock_password", timeout=timeout)

    with requests_mock.mock() as rqst:
        rqst.request(requests_mock.ANY, requests_mock.ANY, exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.query(**small_query)

        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")

        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.download("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")

        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.download_all(["8df46c9e-a20c-43db-a19a-4240c2ed3b8b"])

    with requests_mock.mock() as rqst:
        rqst.request(requests_mock.ANY, requests_mock.ANY, exc=requests.exceptions.ReadTimeout)
        with pytest.raises(requests.exceptions.ReadTimeout):
            api.query(**small_query)

        with pytest.raises(requests.exceptions.ReadTimeout):
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")

        with pytest.raises(requests.exceptions.ReadTimeout):
            api.download("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")

        with pytest.raises(requests.exceptions.ReadTimeout):
            api.download_all(["8df46c9e-a20c-43db-a19a-4240c2ed3b8b"])


@pytest.mark.mock_api
def test_get_products_invalid_json(test_wkt):
    api = SentinelAPI("mock_user", "mock_password")
    with requests_mock.mock() as rqst:
        rqst.post(
            "https://scihub.copernicus.eu/apihub/search?format=json",
            text="{Invalid JSON response",
            status_code=200,
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.query(area=test_wkt, date=("20151219", "20151228"), platformname="Sentinel-2")
        assert excinfo.value.msg == "Invalid API response."


@pytest.mark.scihub
def test_get_products_size(api, vcr, products):
    assert SentinelAPI.get_products_size(products) == 75.4

    # load a new very small query
    with vcr.use_cassette("test_get_products_size"):
        products = api.query(
            raw="S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E"
        )
    assert len(products) > 0
    # Rounded to zero
    assert SentinelAPI.get_products_size(products) == 0


@pytest.mark.scihub
def test_response_to_dict(raw_products):
    dictionary = _parse_opensearch_response(raw_products)
    # check the type
    assert isinstance(dictionary, dict)
    # check if dictionary has id key
    assert "bd1204f7-71ba-4b67-a5f4-df16fbb10138" in dictionary
    props = dictionary["bd1204f7-71ba-4b67-a5f4-df16fbb10138"]
    expected_title = "S2A_MSIL1C_20151223T142942_N0201_R053_T20MNC_20151223T143132"
    assert props["title"] == expected_title


@pytest.mark.vcr
@pytest.mark.scihub
def test_check_existing(api, tmpdir, smallest_online_products, smallest_archived_products):
    ids = [product["id"] for product in smallest_online_products]
    names = [product["title"] for product in smallest_online_products]
    paths = [tmpdir.join(fn + ".zip") for fn in names]
    path_strings = list(map(str, paths))

    # Init files used for testing
    api.download(ids[0], str(tmpdir))
    # File #1: complete and correct
    assert paths[0].check(exists=1, file=1)
    # File #2: complete but incorrect
    with paths[1].open("wb") as f:
        size = 130102
        f.seek(size - 1)
        f.write(b"\0")
    # File #3: incomplete
    dummy_content = b"aaaaaaaaaaaaaaaaaaaaaaaaa"
    with paths[2].open("wb") as f:
        f.write(dummy_content)
    assert paths[2].check(exists=1, file=1)

    # Test
    expected = {str(paths[1]), str(paths[2])}

    def check_result(result, expected_existing):
        assert set(result) == expected
        assert result[paths[1]][0]["id"] == ids[1]
        assert result[paths[2]][0]["id"] == ids[2]
        assert [p.check(exists=1, file=1) for p in paths] == expected_existing

    result = api.check_files(ids=ids, directory=str(tmpdir))
    check_result(result, [True, True, True])

    result = api.check_files(paths=path_strings)
    check_result(result, [True, True, True])

    result = api.check_files(paths=path_strings, delete=True)
    check_result(result, [True, False, False])

    missing_file = str(tmpdir.join(smallest_archived_products[0]["title"] + ".zip"))
    result = api.check_files(paths=[missing_file])
    assert set(result) == {missing_file}
    assert result[missing_file][0]["id"] == smallest_archived_products[0]["id"]

    with pytest.raises(ValueError):
        api.check_files(ids=ids)

    with pytest.raises(ValueError):
        api.check_files()

    tmpdir.remove()
