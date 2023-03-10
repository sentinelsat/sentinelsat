"""
Tests for functionality related to the OData API of SciHub (https://apihub.copernicus.eu/apihub/odata/v1/...)
"""
from datetime import datetime

import pytest
import requests_mock

from sentinelsat import SentinelAPI
from sentinelsat.exceptions import InvalidKeyError, ServerError
from sentinelsat.sentinel import _parse_odata_timestamp
from .conftest import chain, scrub_string


@pytest.fixture
def odata_product_ids():
    return [
        "11af8bd9-24d0-4401-9789-b7b73786e122",
        "16c595db-cd1b-4278-a053-982239b3090b",
        "5e6d1024-ae4f-4a37-8dba-e27c9e0ed0db",
    ]


@pytest.mark.fast
def test_convert_timestamp():
    assert _parse_odata_timestamp("/Date(1445588544652)/") == datetime(
        2015, 10, 23, 8, 22, 24, 652000
    )


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_odata_short(api, odata_product_ids, read_yaml):
    responses = {}
    for id in odata_product_ids:
        responses[id] = api.get_product_odata(id)
    expected = read_yaml("odata_response_short.yml", responses)
    assert sorted(responses) == sorted(expected)


@pytest.mark.scihub
def test_get_product_odata_short_with_missing_online_key(api, vcr):
    uuid = "8df46c9e-a20c-43db-a19a-4240c2ed3b8b"
    expected_short = {
        "id": "8df46c9e-a20c-43db-a19a-4240c2ed3b8b",
        "size": 143549851,
        "md5": "d5e4df5c38c6e97bf7e7bd540ab21c05",
        "url": "https://apihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
        "quicklook_url": "https://apihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/Products('Quicklook')/$value",
        "date": datetime(2015, 11, 21, 10, 3, 56, 675000),
        "footprint": "POLYGON((-63.852531 -5.880887,-67.495872 -5.075419,-67.066071 -3.084356,-63.430576 -3.880541,"
        "-63.852531 -5.880887))",
        "title": "S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC",
        "product_root_dir": "S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC.SAFE",
        "manifest_name": "manifest.safe",
        "Online": True,
        "Creation Date": datetime(2015, 11, 21, 13, 22, 1, 652000),
        "Ingestion Date": datetime(2015, 11, 21, 13, 22, 4, 992000),
    }

    for _ in range(2):
        # scrub 'Online' key from response
        with vcr.use_cassette(
            "test_get_product_odata_short_with_missing_online_key",
            before_record_response=chain(
                vcr.before_record_response, scrub_string(b'"Online":false,', b"")
            ),
        ):
            response = api.get_product_odata(uuid)
    assert response == expected_short


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_odata_full(api, odata_product_ids, read_yaml):
    responses = {}
    for id in odata_product_ids:
        responses[id] = api.get_product_odata(id, full=True)
    expected = read_yaml("odata_response_full.yml", responses)
    assert sorted(responses) == sorted(expected)


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_info_bad_key(api):
    with pytest.raises(InvalidKeyError) as excinfo:
        api.get_product_odata("invalid-xyz")
    assert str(excinfo.value) == "Invalid key (invalid-xyz) to access Products"


@pytest.mark.mock_api
def test_get_product_odata_scihub_down(read_fixture_file):
    api = SentinelAPI("mock_user", "mock_password")

    request_url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')?$format=json"

    with requests_mock.mock() as rqst:
        rqst.get(request_url, text="Mock SciHub is Down", status_code=503)
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert str(excinfo.value) == "HTTP status 503: Mock SciHub is Down"

        rqst.get(
            request_url,
            text='{"error":{"code":null,"message":{"lang":"en","value":'
            "\"No Products found with key '8df46c9e-a20c-43db-a19a-4240c2ed3b8b' \"}}}",
            status_code=500,
        )
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert (
            str(excinfo.value)
            == "HTTP status 500: No Products found with key '8df46c9e-a20c-43db-a19a-4240c2ed3b8b' "
        )

        rqst.get(request_url, text="Mock SciHub is Down", status_code=200)
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert str(excinfo.value) == "HTTP status 200: Mock SciHub is Down"

        # Test with a real "server under maintenance" response
        rqst.get(request_url, text=read_fixture_file("server_maintenance.html"), status_code=502)
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
        assert "The Sentinels Scientific Data Hub will be back soon!" in excinfo.value.msg


@pytest.mark.vcr
@pytest.mark.mock_api
@pytest.mark.scihub
def test_is_online(api):
    uuid = "98ca202b-2155-4181-be88-4358b2cbaaa0"
    invalid_uuid = "98ca202b-2155-4181-be88-xxxxxxxxxxxx"

    request_url = "https://apihub.copernicus.eu/apihub/odata/v1/Products('{}')/Online/$value"

    with requests_mock.mock() as rqst:
        rqst.get(request_url.format(uuid), text="true", status_code=200)
        assert api.is_online(uuid) is True

    with requests_mock.mock() as rqst:
        rqst.get(request_url.format(uuid), text="false", status_code=200)
        assert api.is_online(uuid) is False

    with pytest.raises(InvalidKeyError) as excinfo:
        api.is_online(invalid_uuid)

    with requests_mock.mock() as rqst:
        with pytest.raises(ServerError) as excinfo:
            rqst.get(
                request_url.format(invalid_uuid), status_code=500, headers={"cause-message": "..."}
            )
            assert api.is_online(invalid_uuid)

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url.format(invalid_uuid),
            status_code=500,
            headers={
                "cause-message": "UriNotMatchingException : Could not find property with name: 'Online'."
            },
        )
        assert api.is_online(invalid_uuid) is True
    # assert that no more queries are made after this
    assert api.is_online(invalid_uuid) is True
