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
    with open("tests/expected_search_footprints_s1.geojson", "rb") as testfile:
        testfile_md5.update(testfile.read())
        real_md5 = testfile_md5.hexdigest()
    assert md5_compare("tests/expected_search_footprints_s1.geojson", real_md5) is True
    assert md5_compare("tests/map.geojson", real_md5) is False


@pytest.mark.scihub
def test_SentinelAPI_connection():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query('0 0,1 1,0 1,0 0', datetime(2015, 1, 1), datetime(2015, 1, 2))

    assert api.url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000'
    assert api.query == '(beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z]) ' + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'
    assert api.content.status_code == 200


@pytest.mark.scihub
def test_SentinelAPI_wrong_credentials():
    api = SentinelAPI(
        "wrong_user",
        "wrong_password"
        )
    api.query('0 0,1 1,0 1,0 0', datetime(2015, 1, 1), datetime(2015, 1, 2))
    assert api.content.status_code == 401

    with pytest.raises(ValueError):
        api.get_products_size()
        api.get_products()


@pytest.mark.fast
def test_api_url_format():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )

    now = datetime.now()
    api.format_url('0 0,1 1,0 1,0 0', end_date=now)
    last_24h = format_date(now - timedelta(hours=24))
    assert api.url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000'
    assert api.query == '(beginPosition:[%s TO %s]) ' % (last_24h, format_date(now)) + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'

    api.format_url('0 0,1 1,0 1,0 0', end_date=now, producttype='SLC')
    assert api.url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000'
    assert api.query == '(beginPosition:[%s TO %s]) ' % (last_24h, format_date(now)) + \
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

    assert api.url == 'https://scihub.copernicus.eu/dhus/search?format=json&rows=15000'
    assert api.query == '(beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z]) ' + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'
    assert api.content.status_code == 200


@pytest.mark.fast
def test_trail_slash_base_url():
    base_urls = [
        'https://scihub.copernicus.eu/dhus/',
        'https://scihub.copernicus.eu/dhus'
        ]

    expected = 'https://scihub.copernicus.eu/dhus/'

    for test_url in base_urls:
        assert SentinelAPI._url_trail_slash(test_url) == expected
        api = SentinelAPI(
            environ.get('SENTINEL_USER'),
            environ.get('SENTINEL_PASSWORD'),
            test_url
            )
        assert api.api_url == expected


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

    expected_s1 = {
        'id': '8df46c9e-a20c-43db-a19a-4240c2ed3b8b',
        'size': int(143549851),
        'md5': 'D5E4DF5C38C6E97BF7E7BD540AB21C05',
        'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
        'date': '2015-11-21T10:03:56Z', 'size': 143549851,
        'footprint': '-5.880887 -63.852531,-5.075419 -67.495872,-3.084356 -67.066071,-3.880541 -63.430576,-5.880887 -63.852531',
        'title': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC'
        }

    expected_s2 = {
        'date': '2015-12-27T14:22:29Z',
        'footprint': '-4.565257232533263 -58.80274769505742,-5.513960396525286 -58.80535376268811,-5.515947033626909 -57.90315169909761,-5.516014389089381 -57.903151791669515,-5.516044812342758 -57.85874693129081,-5.516142631941845 -57.814323596961835,-5.516075248310466 -57.81432351345917,-5.516633044843839 -57.00018056571297,-5.516700066819259 -57.000180565731384,-5.51666329264377 -56.95603179187787,-5.516693539799448 -56.91188395837315,-5.51662651925904 -56.91188396736038,-5.515947927683427 -56.097209386295305,-5.516014937246069 -56.09720929423562,-5.5159111504805916 -56.053056977999596,-5.515874390220655 -56.00892491028779,-5.515807411549814 -56.00892501130261,-5.513685455771881 -55.10621586418906,-4.6092845892233 -55.108821882251775,-4.606372862374043 -54.20840287327946,-3.658594390979672 -54.21169990975238,-2.710949551849636 -54.214267703869346,-2.7127451087194463 -55.15704255065496,-2.71378646425769 -56.0563616875051,-2.7141556791285275 -56.9561852630143,-2.713837142510183 -57.8999998009875,-3.6180222056692726 -57.90079161941062,-3.616721351843382 -58.800616247288836,-4.565257232533263 -58.80274769505742',
        'id': '44517f66-9845-4792-a988-b5ae6e81fd3e',
        'md5': '48C5648C2644CE07207B3C943DEDEB44',
        'size': 5854429622,
        'title': 'S2A_OPER_PRD_MSIL1C_PDMC_20151228T112523_R110_V20151227T142229_20151227T142229',
        'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('44517f66-9845-4792-a988-b5ae6e81fd3e')/$value"
    }

    assert api.get_product_info('8df46c9e-a20c-43db-a19a-4240c2ed3b8b') == expected_s1
    assert api.get_product_info('44517f66-9845-4792-a988-b5ae6e81fd3e') == expected_s2


@pytest.mark.mock_api
def test_get_product_info_scihub_down():
    api = SentinelAPI("mock_user", "mock_password")

    with requests_mock.mock() as rqst:
        rqst.get(
            "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/?$format=json",
            text="Mock SciHub is Down", status_code=503
            )
        with pytest.raises(ValueError) as val_err:
            api.get_product_info('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
            assert val_err.value.message == "Invalid API response. JSON decoding failed."


@pytest.mark.mock_api
def test_get_products_invalid_json():
    api = SentinelAPI("mock_user", "mock_password")
    with requests_mock.mock() as rqst:
        rqst.post(
            'https://scihub.copernicus.eu/apihub/search?format=json&rows=15000',
            text="Invalid JSON response", status_code=200
            )
        api.query(
            area=get_coordinates("tests/map.geojson"),
            initial_date="20151219",
            end_date="20151228",
            platformname="Sentinel-2"
        )
        with pytest.raises(ValueError) as val_err:
            api.get_products()
            assert val_err.value.message == "API response not valid. JSON decoding failed."


@pytest.mark.scihub
def test_footprints_s1():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query(
        get_coordinates('tests/map.geojson'),
        datetime(2014, 10, 10), datetime(2014, 12, 31), producttype="GRD"
        )

    with open('tests/expected_search_footprints_s1.geojson', 'r') as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
        # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
        assert set(api.get_footprints()) == set(expected_footprints)


@pytest.mark.scihub
def test_footprints_s2():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query(
        get_coordinates('tests/map.geojson'),
        "20151219", "20151228", platformname="Sentinel-2"
        )

    with open('tests/expected_search_footprints_s2.geojson', 'r') as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
        # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
        assert set(api.get_footprints()) == set(expected_footprints)


@pytest.mark.scihub
def test_s2_cloudcover():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query(
        get_coordinates('tests/map.geojson'),
        "20151219", "20151228",
        platformname="Sentinel-2",
        cloudcoverpercentage="[0 TO 10]"
        )
    assert len(api.get_products()) == 3
    assert api.get_products()[0]["id"] == "6ed0b7de-3435-43df-98bf-ad63c8d077ef"
    assert api.get_products()[1]["id"] == "37ecee60-23d8-4ec2-a65f-2de24f51d30e"
    assert api.get_products()[2]["id"] == "0848f6b8-5730-4759-850e-fc9945d42296"


@pytest.mark.scihub
def test_get_products_size():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
        )
    api.query(
        get_coordinates('tests/map.geojson'),
        "20151219", "20151228", platformname="Sentinel-2"
        )
    assert api.get_products_size() == 63.58
