import geojson
import pytest
import requests_mock

from datetime import datetime, date, timedelta
from os import environ
import hashlib

from sentinelsat.sentinel import (SentinelAPI, format_date, get_coordinates,
    convert_timestamp, md5_compare)


@pytest.mark.fast
def test_format_date():
    assert format_date(datetime(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_date(date(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_date('2015-01-01T00:00:00Z') == '2015-01-01T00:00:00Z'
    assert format_date('20150101') == '2015-01-01T00:00:00Z'
    assert format_date('NOW') == 'NOW'


@pytest.mark.fast
def test_convert_timestamp():
    assert convert_timestamp('/Date(1445588544652)/') == '2015-10-23T08:22:24Z'


@pytest.mark.fast
def test_md5_comparison():
    testfile_md5 = hashlib.md5()
    with open("tests/expected_search_footprints.geojson", "rb") as testfile:
        testfile_md5.update(testfile.read())
        real_md5 = testfile_md5.hexdigest()
    assert md5_compare("tests/expected_search_footprints.geojson", real_md5) is True
    assert md5_compare("tests/map.geojson", real_md5) is False


@pytest.mark.scihub
def test_SentinelAPI():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query('0 0,1 1,0 1,0 0', datetime(2015, 1, 1), datetime(2015, 1, 2))

    assert api.url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000' + \
        '&q=(ingestionDate:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z]) ' + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'
    assert api.content.status_code == 200

    now = datetime.now()
    api.format_url('0 0,1 1,0 1,0 0', end_date=now)
    last_24h = format_date(now - timedelta(hours=24))
    assert api.url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000' + \
        '&q=(ingestionDate:[%s TO %s]) ' % (last_24h, format_date(now)) + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'

    api.format_url('0 0,1 1,0 1,0 0', end_date=now, producttype='SLC')
    assert api.url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000' + \
        '&q=(ingestionDate:[%s TO %s]) ' % (last_24h, format_date(now)) + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))") ' + \
        'AND (producttype:SLC)'


@pytest.mark.scihub
def test_set_base_url():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD'),
        'https://scihub.copernicus.eu/dhus/'
        )
    api.query('0 0,1 1,0 1,0 0', datetime(2015, 1, 1), datetime(2015, 1, 2))

    assert api.url == 'https://scihub.copernicus.eu/dhus/search?format=json&rows=15000' + \
        '&q=(ingestionDate:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z]) ' + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'
    assert api.content.status_code == 200


@pytest.mark.fast
def test_get_coordinates():
    coords = ('-66.2695312 -8.0592296,-66.2695312 0.7031074,' +
        '-57.3046875 0.7031074,-57.3046875 -8.0592296,-66.2695312 -8.0592296')
    assert get_coordinates('tests/map.geojson') == coords


@pytest.mark.scihub
def test_get_product_info():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )

    expected = {
        'id': '8df46c9e-a20c-43db-a19a-4240c2ed3b8b',
        'size': int(143549851),
        'md5': 'D5E4DF5C38C6E97BF7E7BD540AB21C05',
        'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
        'date': '2015-11-21T10:03:56Z',  'size': 143549851,
        'footprint': '-5.880887 -63.852531,-5.075419 -67.495872,-3.084356 -67.066071,-3.880541 -63.430576,-5.880887 -63.852531',
        'title': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC'
        }
    assert api.get_product_info('8df46c9e-a20c-43db-a19a-4240c2ed3b8b') == expected


@pytest.mark.mock_api
def test_get_product_info_scihub_down():
    api = SentinelAPI("mock_user", "mock_password")
    with requests_mock.mock() as rqst:
        rqst.get(
            "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/?$format=json",
            text="Mock SciHub is Down", status_code=503
            )
        with pytest.raises(ValueError):
            api.get_product_info('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')


@pytest.mark.scihub
def test_footprints():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query(
        get_coordinates('tests/map.geojson'),
        datetime(2014, 10, 10), datetime(2014, 12, 31), producttype="GRD"
        )

    with open('tests/expected_search_footprints.geojson', 'r') as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
        # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
        assert set(api.get_footprints()) == set(expected_footprints)
