"""
Tests for functionality related to the OData API of SciHub (https://scihub.copernicus.eu/apihub/odata/v1/...)
"""
from datetime import datetime

import pytest
import requests_mock

from sentinelsat import SentinelAPIError, SentinelAPI
from sentinelsat.sentinel import _parse_odata_timestamp


@pytest.mark.fast
def test_convert_timestamp():
    assert _parse_odata_timestamp("/Date(1445588544652)/") == datetime(
        2015, 10, 23, 8, 22, 24, 652000
    )


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_odata_short(api, smallest_online_products, read_yaml):
    responses = {}
    for prod in smallest_online_products:
        id = prod["id"]
        responses[id] = api.get_product_odata(id)
    expected = read_yaml("odata_response_short.yml", responses)
    assert sorted(responses) == sorted(expected)


def scrub_string(string, replacement=""):
    """Scrub a string from a VCR response body string
    """

    def before_record_response(response):
        response["body"]["string"] = response["body"]["string"].replace(string, replacement)
        return response

    return before_record_response


@pytest.mark.scihub
def test_get_product_odata_short_with_missing_online_key(api, vcr):
    uuid = "8df46c9e-a20c-43db-a19a-4240c2ed3b8b"
    expected_short = {
        "id": "8df46c9e-a20c-43db-a19a-4240c2ed3b8b",
        "size": 143549851,
        "md5": "D5E4DF5C38C6E97BF7E7BD540AB21C05",
        "url": "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
        "date": datetime(2015, 11, 21, 10, 3, 56, 675000),
        "footprint": "POLYGON((-63.852531 -5.880887,-67.495872 -5.075419,-67.066071 -3.084356,-63.430576 -3.880541,"
        "-63.852531 -5.880887))",
        "title": "S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC",
        "Online": True,
        "Creation Date": datetime(2015, 11, 21, 13, 22, 1, 652000),
        "Ingestion Date": datetime(2015, 11, 21, 13, 22, 4, 992000),
    }

    # scrub 'Online' key from response
    with vcr.use_cassette(
        "test_get_product_odata_short_with_missing_online_key",
        before_record_response=scrub_string(b'"Online":false,', b""),
    ):
        response = api.get_product_odata(uuid)
        assert response == expected_short


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_odata_full(api, smallest_online_products, read_yaml):
    responses = {}
    for prod in smallest_online_products:
        id = prod["id"]
        responses[id] = api.get_product_odata(id, full=True)
    expected = read_yaml("odata_response_full.yml", responses)
    assert sorted(responses) == sorted(expected)


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_info_bad_key(api):
    with pytest.raises(SentinelAPIError) as excinfo:
        api.get_product_odata("invalid-xyz")
    assert excinfo.value.msg == "InvalidKeyException : Invalid key (invalid-xyz) to access Products"


@pytest.mark.mock_api
def test_get_product_odata_scihub_down(read_fixture_file):
    api = SentinelAPI("mock_user", "mock_password")

    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')?$format=json"

    with requests_mock.mock() as rqst:
        rqst.get(request_url, text="Mock SciHub is Down", status_code=503)
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert excinfo.value.msg == "Mock SciHub is Down"

        rqst.get(
            request_url,
            text='{"error":{"code":null,"message":{"lang":"en","value":'
            "\"No Products found with key '8df46c9e-a20c-43db-a19a-4240c2ed3b8b' \"}}}",
            status_code=500,
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert (
            excinfo.value.msg
            == "No Products found with key '8df46c9e-a20c-43db-a19a-4240c2ed3b8b' "
        )

        rqst.get(request_url, text="Mock SciHub is Down", status_code=200)
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert excinfo.value.msg == "Mock SciHub is Down"

        # Test with a real "server under maintenance" response
        rqst.get(request_url, text=read_fixture_file("server_maintenance.html"), status_code=502)
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert "The Sentinels Scientific Data Hub will be back soon!" in excinfo.value.msg


@pytest.mark.mock_api
def test_is_online():
    api = SentinelAPI("mock_user", "mock_password")

    uuid = "98ca202b-2155-4181-be88-4358b2cbaaa0"
    invalid_uuid = "98ca202b-2155-4181-be88-xxxxxxxxxxxx"

    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('{}')/Online/$value"

    with requests_mock.mock() as rqst:
        rqst.get(request_url.format(uuid), text="true", status_code=200)
        assert api.is_online(uuid) == True

    with requests_mock.mock() as rqst:
        rqst.get(request_url.format(uuid), text="false", status_code=200)
        assert api.is_online(uuid) == False

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url.format(invalid_uuid),
            text='{{"error":{{"code":null,"message":{{"lang":"en","value":'
            "Invalid key ({}) to access Products}}}}}}".format(invalid_uuid),
            status_code=200,
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.is_online(invalid_uuid)
