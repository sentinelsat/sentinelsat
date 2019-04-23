# -*- coding: utf-8 -*-
import hashlib
import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import geojson
import py.path
import pytest
import requests
import requests_mock
from requests.exceptions import *

from sentinelsat import *
from sentinelsat.sentinel import _format_order_by, _parse_odata_timestamp, _parse_opensearch_response

_small_query = dict(
    area='POLYGON((0 0,1 1,0 1,0 0))',
    date=(datetime(2015, 1, 1), datetime(2015, 1, 2)))

_large_query = dict(
    area='POLYGON((0 0,0 10,10 10,10 0,0 0))',
    date=(datetime(2015, 12, 1), datetime(2015, 12, 31)))


def test_boundaries_latitude_more(fixture_path):
    with pytest.raises(ValueError):
        geojson_to_wkt(read_geojson(fixture_path('map_boundaries_lat.geojson')))


def test_boundaries_longitude_less(fixture_path):
    with pytest.raises(ValueError):
        geojson_to_wkt(read_geojson(fixture_path('map_boundaries_lon.geojson')))


@pytest.mark.vcr
@pytest.mark.scihub
def test_format_date(api):
    assert format_query_date(datetime(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_query_date(date(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_query_date('2015-01-01T00:00:00Z') == '2015-01-01T00:00:00Z'
    assert format_query_date('20150101') == '2015-01-01T00:00:00Z'
    assert format_query_date(' NOW ') == 'NOW'
    assert format_query_date(None) == '*'

    for date_str in ("NOW", "NOW-1DAY", "NOW-1DAYS", "NOW-500DAY", "NOW-500DAYS",
                     "NOW-2MONTH", "NOW-2MONTHS", "NOW-20MINUTE", "NOW-20MINUTES",
                     "NOW+10HOUR", "2015-01-01T00:00:00Z+1DAY", "NOW+3MONTHS-7DAYS/DAYS",
                     "*"):
        assert format_query_date(date_str) == date_str
        api.query(raw='ingestiondate:[{} TO *]'.format(date_str), limit=0)

    for date_str in ("NOW - 1HOUR", "NOW -   1HOURS", "NOW-1 HOURS", "NOW-1", "NOW-", "**", "+", "-"):
        with pytest.raises(ValueError):
            format_query_date(date_str)
        with pytest.raises(QuerySyntaxError):
            api.query(raw='ingestiondate:[{} TO *]'.format(date_str), limit=0)


@pytest.mark.fast
def test_convert_timestamp():
    assert _parse_odata_timestamp('/Date(1445588544652)/') == datetime(2015, 10, 23, 8, 22, 24, 652000)


@pytest.mark.fast
def test_progressbars(capsys, fixture_path):
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
@pytest.mark.scihub
def test_SentinelAPI_connection(api):
    api.query(**_small_query)
    assert api._last_query == (
        'beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z] '
        'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"')
    assert api._last_response.status_code == 200


@pytest.mark.vcr
@pytest.mark.scihub
def test_SentinelAPI_wrong_credentials():
    api = SentinelAPI(
        "wrong_user",
        "wrong_password"
    )

    @contextmanager
    def assert_exception():
        with pytest.raises(UnauthorizedError) as excinfo:
            yield
        assert excinfo.value.response.status_code == 401
        assert 'Invalid user name or password' in excinfo.value.msg

    with assert_exception():
        api.query(**_small_query)
    with assert_exception():
        api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
    with assert_exception():
        api.download('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
    with assert_exception():
        api.download_all(['8df46c9e-a20c-43db-a19a-4240c2ed3b8b'])


@pytest.mark.vcr
@pytest.mark.scihub
@pytest.mark.parametrize('exception', [
    StreamConsumedError,
    ContentDecodingError,
    InvalidProxyURL,
    InvalidHeader,
    TooManyRedirects,
    ReadTimeout,
    SSLError
])
def test_requests_error(exception, api):
    """non-HTTP errors originating from requests should be raised directly without translating them"""
    with requests_mock.mock() as rqst:
        rqst.register_uri(requests_mock.ANY, requests_mock.ANY, exc=exception)
        with pytest.raises(exception):
            api.query(**_small_query)

        with pytest.raises(exception):
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(exception):
            api.download('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(exception):
            api.download_all(['8df46c9e-a20c-43db-a19a-4240c2ed3b8b'])


@pytest.mark.fast
def test_api_query_format():
    wkt = 'POLYGON((0 0,1 1,0 1,0 0))'

    now = datetime.now()
    last_24h = format_query_date(now - timedelta(hours=24))
    query = SentinelAPI.format_query(wkt, (last_24h, now))
    assert query == 'beginPosition:[%s TO %s] ' % (last_24h, format_query_date(now)) + \
           'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'

    query = SentinelAPI.format_query(wkt, date=(last_24h, "NOW"), producttype='SLC', raw='IW')
    assert query == 'beginPosition:[%s TO NOW] ' % (format_query_date(last_24h)) + \
           'producttype:SLC IW footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'

    query = SentinelAPI.format_query(wkt, producttype='SLC', raw='IW')
    assert query == 'producttype:SLC IW footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'

    query = SentinelAPI.format_query(area=None, date=None)
    assert query == ''

    query = SentinelAPI.format_query()
    assert query == ''

    query = SentinelAPI.format_query(raw='test')
    assert query == 'test'


@pytest.mark.fast
def test_api_query_format_with_duplicates():
    with pytest.raises(ValueError) as excinfo:
        SentinelAPI.format_query(date=('NOW-1DAY', 'NOW'), beginPosition=('NOW-3DAY', 'NOW'))
    assert 'duplicate' in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        SentinelAPI.format_query(ingestiondate=('NOW-1DAY', 'NOW'), ingestionDate=('NOW-3DAY', 'NOW'))
    assert 'duplicate' in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        SentinelAPI.format_query(area='POINT(0, 0)', footprint='POINT(0, 0)')
    assert 'duplicate' in str(excinfo.value)


@pytest.mark.fast
def test_api_query_format_ranges():
    query = SentinelAPI.format_query(cloudcoverpercentage=(0, 30))
    assert query == 'cloudcoverpercentage:[0 TO 30]'

    query = SentinelAPI.format_query(cloudcoverpercentage=[0, 30])
    assert query == 'cloudcoverpercentage:[0 TO 30]'

    query = SentinelAPI.format_query(cloudcoverpercentage=[None, 30])
    assert query == 'cloudcoverpercentage:[* TO 30]'

    query = SentinelAPI.format_query(orbitnumber=(16302, None))
    assert query == 'orbitnumber:[16302 TO *]'

    query = SentinelAPI.format_query(orbitnumber=(16302, '*'))
    assert query == 'orbitnumber:[16302 TO *]'

    for value in [(None, None), ('*', None), (None, '*'), ('*', '*')]:
        query = SentinelAPI.format_query(orbitnumber=value)
        assert query == ''

    with pytest.raises(ValueError):
        SentinelAPI.format_query(cloudcoverpercentage=[])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(cloudcoverpercentage=[0])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(cloudcoverpercentage=[0, 1, 2])


@pytest.mark.fast
def test_api_query_format_dates():
    query = SentinelAPI.format_query(ingestiondate=('NOW-1DAY', 'NOW'))
    assert query == 'ingestiondate:[NOW-1DAY TO NOW]'

    query = SentinelAPI.format_query(ingestiondate=(date(2017, 1, 1), '20170203'))
    assert query == 'ingestiondate:[2017-01-01T00:00:00Z TO 2017-02-03T00:00:00Z]'

    query = SentinelAPI.format_query(ingestiondate='[NOW-1DAY TO NOW]')
    assert query == 'ingestiondate:[NOW-1DAY TO NOW]'

    query = SentinelAPI.format_query(ingestiondate=[None, 'NOW'])
    assert query == 'ingestiondate:[* TO NOW]'

    for value in [(None, None), ('*', None), (None, '*'), ('*', '*')]:
        query = SentinelAPI.format_query(ingestiondate=value)
        assert query == ''

    with pytest.raises(ValueError):
        SentinelAPI.format_query(date="NOW")

    with pytest.raises(ValueError):
        SentinelAPI.format_query(date=["NOW"])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(ingestiondate=[])


@pytest.mark.vcr
@pytest.mark.scihub
def test_api_query_format_escape_spaces(api):
    query = SentinelAPI.format_query(ingestiondate=('NOW-1DAY', 'NOW'))
    assert query == 'ingestiondate:[NOW-1DAY TO NOW]'

    query = SentinelAPI.format_query(ingestiondate='[NOW-1DAY TO NOW]')
    assert query == 'ingestiondate:[NOW-1DAY TO NOW]'

    query = SentinelAPI.format_query(ingestiondate=' [NOW-1DAY TO NOW] ')
    assert query == 'ingestiondate:[NOW-1DAY TO NOW]'

    query = SentinelAPI.format_query(relativeorbitnumber=' {101 TO 103} ')
    assert query == 'relativeorbitnumber:{101 TO 103}'

    query = SentinelAPI.format_query(filename='S3A_OL_2* ')
    assert query == 'filename:S3A_OL_2*'

    query = SentinelAPI.format_query(timeliness='Non Time Critical')
    assert query == r'timeliness:Non\ Time\ Critical'

    query = SentinelAPI.format_query(timeliness='Non\tTime\tCritical')
    assert query == r'timeliness:Non\ Time\ Critical'

    assert api.count(timeliness='Non Time Critical') > 0

    # Allow for regex weirdness
    query = SentinelAPI.format_query(timeliness='.+ Critical')
    assert query == r'timeliness:.+\ Critical'
    assert api.count(timeliness='.+ Critical') > 0

    query = SentinelAPI.format_query(identifier='/S[123 ]A.*/')
    assert query == r'identifier:/S[123 ]A.*/'
    assert api.count(identifier='/S[123 ]A.*/') > 0


@pytest.mark.vcr
@pytest.mark.scihub
def test_invalid_query(api):
    with pytest.raises(QuerySyntaxError):
        api.query(raw="xxx:yyy")


@pytest.mark.fast
def test_format_url(api):
    start_row = 0
    url = api._format_url(offset=start_row)
    assert url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}'.format(
        rows=api.page_size, start=start_row)
    limit = 50
    url = api._format_url(limit=limit, offset=start_row)
    assert url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}'.format(
        rows=limit, start=start_row)
    url = api._format_url(limit=api.page_size + 50, offset=start_row)
    assert url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}'.format(
        rows=api.page_size, start=start_row)
    url = api._format_url(order_by="beginposition desc", limit=api.page_size + 50, offset=10)
    assert url == 'https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}' \
                  '&orderby={orderby}'.format(rows=api.page_size, start=10,
                                              orderby="beginposition desc")


@pytest.mark.fast
def test_format_url_custom_api_url():
    api = SentinelAPI("user", "pw", api_url='https://scihub.copernicus.eu/dhus/')
    url = api._format_url()
    assert url.startswith('https://scihub.copernicus.eu/dhus/search')

    api = SentinelAPI("user", "pw", api_url='https://scihub.copernicus.eu/dhus')
    url = api._format_url()
    assert url.startswith('https://scihub.copernicus.eu/dhus/search')


@pytest.mark.fast
def test_format_order_by():
    res = _format_order_by("cloudcoverpercentage")
    assert res == "cloudcoverpercentage asc"

    res = _format_order_by("+cloudcoverpercentage,-beginposition")
    assert res == "cloudcoverpercentage asc,beginposition desc"

    res = _format_order_by(" +cloudcoverpercentage, -beginposition ")
    assert res == "cloudcoverpercentage asc,beginposition desc"

    with pytest.raises(ValueError):
        _format_order_by("+cloudcoverpercentage-beginposition")


@pytest.mark.vcr
@pytest.mark.scihub
def test_small_query(api):
    api.query(**_small_query)
    assert api._last_query == (
        'beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z] '
        'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"')
    assert api._last_response.status_code == 200


@pytest.mark.vcr(decode_compressed_response=False)
@pytest.mark.scihub
def test_large_query(api):
    full_products = list(api.query(**_large_query))
    assert api._last_query == (
        'beginPosition:[2015-12-01T00:00:00Z TO 2015-12-31T00:00:00Z] '
        'footprint:"Intersects(POLYGON((0 0,0 10,10 10,10 0,0 0)))"')
    assert api._last_response.status_code == 200
    assert len(full_products) > api.page_size

    result = list(api.query(limit=150, **_large_query))
    assert result == full_products[:150]

    result = list(api.query(limit=20, offset=90, **_large_query))
    assert result == full_products[90:110]

    result = list(api.query(limit=20, offset=len(full_products) - 10, **_large_query))
    assert result == full_products[-10:]


@pytest.mark.vcr
@pytest.mark.scihub
def test_count(api):
    count = api.count(None, ("20150101", "20151231"))
    assert count > 100000


# @pytest.mark.vcr
@pytest.mark.skip(reason="Cannot mock since VCR.py has issues with Unicode request bodies.")
@pytest.mark.scihub
def test_unicode_support(api):
    test_str = u'٩(●̮̮̃•̃)۶:'

    with pytest.raises(QuerySyntaxError) as excinfo:
        api.count(raw=test_str)
    assert test_str == excinfo.value.response.json()['feed']['opensearch:Query']['searchTerms']

    with pytest.raises(InvalidKeyException) as excinfo:
        api.get_product_odata(test_str)
    assert test_str in excinfo.value.response.json()['error']['message']['value']


@pytest.mark.vcr
@pytest.mark.scihub
def test_too_long_query(api):
    # Test whether our limit calculation is reasonably correct and
    # that a relevant error message is provided

    def create_query(n):
        return " a_-.*:,?+~!" * n

    # Expect no error
    q = create_query(163)
    assert 0.99 < SentinelAPI.check_query_length(q) < 1.0
    with pytest.raises(QuerySyntaxError) as excinfo:
        api.count(raw=q)
    assert "Invalid query string" in excinfo.value.msg

    q = create_query(164)
    assert 0.999 <= SentinelAPI.check_query_length(q) < 1.01
    with pytest.raises(QueryLengthError) as excinfo:
        api.count(raw=q)
    assert "x times the maximum allowed" in excinfo.value.msg


@pytest.mark.vcr
@pytest.mark.scihub
def test_date_arithmetic(api):
    products = api.query('ENVELOPE(0, 1, 1, 0)',
                         ('2016-12-01T00:00:00Z-1DAY',
                          '2016-12-01T00:00:00Z+1DAY-1HOUR'))
    assert api._last_response.status_code == 200
    assert 0 < len(products) < 30


@pytest.mark.vcr
@pytest.mark.scihub
def test_quote_symbol_bug(api):
    # A test to check if plus symbol handling works correctly on the server side
    # It used to raise an error but has since been fixed
    # https://github.com/SentinelDataHub/DataHubSystem/issues/23

    q = 'beginposition:[2017-05-30T00:00:00Z TO 2017-05-31T00:00:00Z+1DAY]'
    count = api.count(raw=q)
    assert count > 0


@pytest.mark.fast
def test_get_coordinates(fixture_path):
    wkt = ('POLYGON((-66.2695 -8.0592,-66.2695 0.7031,'
           '-57.3047 0.7031,-57.3047 -8.0592,-66.2695 -8.0592))')
    assert geojson_to_wkt(read_geojson(fixture_path('map.geojson'))) == wkt
    assert geojson_to_wkt(read_geojson(fixture_path('map_z.geojson'))) == wkt
    assert geojson_to_wkt(read_geojson(fixture_path('map_nested.geojson'))) == wkt


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_odata_short(api, smallest_online_products, read_yaml):
    responses = {}
    for prod in smallest_online_products:
        id = prod['id']
        responses[id] = api.get_product_odata(id)
    expected = read_yaml('odata_response_short.yml', responses)
    assert responses == expected


def scrub_string(string, replacement=''):
    """Scrub a string from a VCR response body string
    """

    def before_record_response(response):
        response['body']['string'] = response['body']['string'].replace(string, replacement)
        return response

    return before_record_response


@pytest.mark.scihub
def test_get_product_odata_short_with_missing_online_key(api, vcr):
    uuid = '8df46c9e-a20c-43db-a19a-4240c2ed3b8b'
    expected_short = {
        'id': '8df46c9e-a20c-43db-a19a-4240c2ed3b8b',
        'size': 143549851,
        'md5': 'D5E4DF5C38C6E97BF7E7BD540AB21C05',
        'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
        'date': datetime(2015, 11, 21, 10, 3, 56, 675000),
        'footprint': 'POLYGON((-63.852531 -5.880887,-67.495872 -5.075419,-67.066071 -3.084356,-63.430576 -3.880541,'
                     '-63.852531 -5.880887))',
        'title': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC',
        'Online': True,
        'Creation Date': datetime(2015, 11, 21, 13, 22, 1, 652000),
        'Ingestion Date': datetime(2015, 11, 21, 13, 22, 4, 992000),
    }

    # scrub 'Online' key from response
    with vcr.use_cassette("test_get_product_odata_short_with_missing_online_key",
                          before_record_response=scrub_string(b'"Online":false,', b'')):
        response = api.get_product_odata(uuid)
        assert response == expected_short


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_odata_full(api, smallest_online_products, read_yaml):
    responses = {}
    for prod in smallest_online_products:
        id = prod['id']
        responses[id] = api.get_product_odata(id, full=True)
    expected = read_yaml('odata_response_full.yml', responses)
    assert responses == expected


@pytest.mark.vcr
@pytest.mark.scihub
def test_get_product_info_bad_key(api):
    with pytest.raises(InvalidKeyException) as excinfo:
        api.get_product_odata('invalid-xyz')
    assert excinfo.value.msg == "Invalid key (invalid-xyz) to access Products"


@pytest.mark.mock_api
def test_get_product_odata_scihub_down(read_fixture_file):
    api = SentinelAPI("mock_user", "mock_password")

    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')?$format=json"

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url,
            text="Mock SciHub is Down", status_code=503
        )
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert excinfo.value.msg == "Mock SciHub is Down"

        rqst.get(
            request_url,
            text='{"error":{"code":null,"message":{"lang":"en","value":'
                 '"No Products found with key \'8df46c9e-a20c-43db-a19a-4240c2ed3b8b\' "}}}',
            status_code=500
        )
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert excinfo.value.msg == "No Products found with key \'8df46c9e-a20c-43db-a19a-4240c2ed3b8b\' "

        rqst.get(
            request_url,
            text="Mock SciHub is Down", status_code=200
        )
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert excinfo.value.msg == "Mock SciHub is Down"

        # Test with a real "server under maintenance" response
        rqst.get(
            request_url,
            text=read_fixture_file('server_maintenance.html'),
            status_code=502)
        with pytest.raises(ServerError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert "The Sentinels Scientific Data Hub will be back soon!" in excinfo.value.msg


@pytest.mark.mock_api
def test_scihub_unresponsive():
    timeout_connect = 6
    timeout_read = 6.6
    timeout = (timeout_connect, timeout_read)

    api = SentinelAPI("mock_user", "mock_password", timeout=timeout)

    with requests_mock.mock() as rqst:
        rqst.request(requests_mock.ANY, requests_mock.ANY, exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.query(**_small_query)

        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.download('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(requests.exceptions.ConnectTimeout):
            api.download_all(['8df46c9e-a20c-43db-a19a-4240c2ed3b8b'])

    with requests_mock.mock() as rqst:
        rqst.request(requests_mock.ANY, requests_mock.ANY, exc=requests.exceptions.ReadTimeout)
        with pytest.raises(requests.exceptions.ReadTimeout):
            api.query(**_small_query)

        with pytest.raises(requests.exceptions.ReadTimeout):
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(requests.exceptions.ReadTimeout):
            api.download('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(requests.exceptions.ReadTimeout):
            api.download_all(['8df46c9e-a20c-43db-a19a-4240c2ed3b8b'])


def test_trigger_lta_accepted():
    api = SentinelAPI("mock_user", "mock_password")

    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value"

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url,
            text="Mock trigger accepted", status_code=202
        )
        assert api._trigger_offline_retrieval(request_url) == 202


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


@pytest.mark.mock_api
def test_get_products_invalid_json(test_wkt):
    api = SentinelAPI("mock_user", "mock_password")
    with requests_mock.mock() as rqst:
        rqst.post(
            'https://scihub.copernicus.eu/apihub/search?format=json',
            text="{Invalid JSON response", status_code=200
        )
        with pytest.raises(ServerError) as excinfo:
            api.query(
                area=test_wkt,
                date=("20151219", "20151228"),
                platformname="Sentinel-2"
            )
        assert excinfo.value.msg == "Invalid API response"


@pytest.mark.vcr
@pytest.mark.scihub
def test_footprints_s1(api, test_wkt, read_fixture_file):
    products = api.query(
        test_wkt,
        (datetime(2014, 10, 10), datetime(2014, 12, 31)),
        producttype="GRD"
    )

    footprints = api.to_geojson(products)
    for footprint in footprints['features']:
        assert not footprint['geometry'].errors()

    expected_footprints = geojson.loads(read_fixture_file('expected_search_footprints_s1.geojson'))
    # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
    assert set(footprints) == set(expected_footprints)


@pytest.mark.scihub
def test_footprints_s2(products, fixture_path):
    footprints = SentinelAPI.to_geojson(products)
    for footprint in footprints['features']:
        assert not footprint['geometry'].errors()

    with open(fixture_path('expected_search_footprints_s2.geojson')) as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
    # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
    assert set(footprints) == set(expected_footprints)


@pytest.mark.vcr
@pytest.mark.scihub
def test_s2_cloudcover(api, test_wkt):
    products = api.query(
        test_wkt,
        ("20181212", "20181228"),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 10)
    )

    product_ids = list(products)
    assert product_ids == [
        'bf652bc4-299c-4c39-9238-ee5a3fdc0d3e',
        'b508a8cd-c7d6-4a4d-9286-6d9463926554',
        'c9b0a744-c0e5-41f9-af6c-f0af83681e58',
        '2e69293b-591f-41d4-99e5-89ec087ae487',
        'dcd0849f-f43a-46f4-9267-da8069b74dd8'
    ]

    # For order-by test
    vals = [x["cloudcoverpercentage"] for x in products.values()]
    assert sorted(vals) != vals
    assert all(0 <= x <= 10 for x in vals)


@pytest.mark.vcr
@pytest.mark.scihub
def test_order_by(api, test_wkt):
    kwargs = dict(
        area=test_wkt,
        date=("20151219", "20160519"),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 10),
        order_by="cloudcoverpercentage, -beginposition"
    )
    # Check that order_by works correctly also in cases where pagination is required
    expected_count = api.count(**kwargs)
    assert 100 < expected_count < 250
    products = api.query(**kwargs)
    assert len(products) == expected_count
    vals = [x["cloudcoverpercentage"] for x in products.values()]
    assert sorted(vals) == vals
    assert all(0 <= x <= 10 for x in vals)


@pytest.mark.vcr
@pytest.mark.scihub
def test_area_relation(api):
    params = dict(
        area="POLYGON((10.83 53.04,11.64 53.04,11.64 52.65,10.83 52.65,10.83 53.04))",
        date=("20151219", "20151226")
    )
    result = api.query(**params)
    n_intersects = len(result)
    assert n_intersects > 10

    result = api.query(area_relation="contains", **params)
    n_contains = len(result)
    assert 0 < n_contains < n_intersects
    result = api.query(area_relation="IsWithin", **params)
    n_iswithin = len(result)
    assert n_iswithin == 0

    # Check that unsupported relations raise an error
    with pytest.raises(ValueError):
        api.query(area_relation="disjoint", **params)


@pytest.mark.scihub
def test_get_products_size(api, vcr, products):
    assert SentinelAPI.get_products_size(products) == 75.4

    # load a new very small query
    with vcr.use_cassette('test_get_products_size'):
        products = api.query(
            raw="S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E")
    assert len(products) > 0
    # Rounded to zero
    assert SentinelAPI.get_products_size(products) == 0


@pytest.mark.scihub
def test_response_to_dict(raw_products):
    dictionary = _parse_opensearch_response(raw_products)
    # check the type
    assert isinstance(dictionary, dict)
    # check if dictionary has id key
    assert 'bd1204f7-71ba-4b67-a5f4-df16fbb10138' in dictionary
    props = dictionary['bd1204f7-71ba-4b67-a5f4-df16fbb10138']
    expected_title = 'S2A_MSIL1C_20151223T142942_N0201_R053_T20MNC_20151223T143132'
    assert props['title'] == expected_title


@pytest.mark.fast
@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.skipif(sys.version_info <= (3, 4),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_missing_dependency_dataframe(monkeypatch):
    api = SentinelAPI("mock_user", "mock_password")

    with pytest.raises(ImportError):
        monkeypatch.setitem(sys.modules, "pandas", None)
        api.to_dataframe({"test": "test"})

    with pytest.raises(ImportError):
        monkeypatch.setitem(sys.modules, "geopandas", None)
        api.to_geodataframe({"test": "tst"})


@pytest.mark.pandas
@pytest.mark.scihub
@pytest.mark.skipif(sys.version_info < (3, 5),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_to_pandas(products):
    df = SentinelAPI.to_dataframe(products)
    assert type(df).__name__ == 'DataFrame'
    assert len(products) == len(df)
    assert set(products) == set(df.index)


@pytest.mark.pandas
@pytest.mark.scihub
@pytest.mark.skipif(sys.version_info < (3, 5),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_to_pandas_empty(products):
    df = SentinelAPI.to_dataframe({})
    assert type(df).__name__ == 'DataFrame'
    assert len(df) == 0


@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.scihub
@pytest.mark.skipif(sys.version_info < (3, 5),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_to_geopandas(products):
    gdf = SentinelAPI.to_geodataframe(products)
    assert type(gdf).__name__ == 'GeoDataFrame'
    print(gdf.unary_union.area)
    assert gdf.unary_union.area == pytest.approx(89.6, abs=0.1)
    assert len(gdf) == len(products)
    assert gdf.crs == {'init': 'epsg:4326'}


@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.scihub
@pytest.mark.skipif(sys.version_info < (3, 5),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_to_geopandas_empty(products):
    gdf = SentinelAPI.to_geodataframe({})
    assert type(gdf).__name__ == 'GeoDataFrame'
    assert len(gdf) == 0


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
    with pytest.raises(InvalidKeyException) as excinfo:
        api.download(uuid)
    assert 'Invalid key' in excinfo.value.msg


@pytest.mark.vcr
@pytest.mark.scihub
def test_query_by_names(api, smallest_online_products):
    names = [product['title'] for product in smallest_online_products]
    expected = {product['title']: {product['id']} for product in smallest_online_products}

    result = api._query_names(names)
    assert list(result) == names
    for name in names:
        assert set(result[name]) == expected[name]

    result2 = api._query_names(names * 100)
    assert result == result2


@pytest.mark.vcr
@pytest.mark.scihub
def test_check_existing(api, tmpdir, smallest_online_products, smallest_archived_products):
    ids = [product['id'] for product in smallest_online_products]
    names = [product['title'] for product in smallest_online_products]
    paths = [tmpdir.join(fn + '.zip') for fn in names]
    path_strings = list(map(str, paths))

    # Init files used for testing
    api.download(ids[0], str(tmpdir))
    # File #1: complete and correct
    assert paths[0].check(exists=1, file=1)
    # File #2: complete but incorrect
    with paths[1].open("wb") as f:
        size = 130102
        f.seek(size - 1)
        f.write(b'\0')
    # File #3: incomplete
    dummy_content = b'aaaaaaaaaaaaaaaaaaaaaaaaa'
    with paths[2].open("wb") as f:
        f.write(dummy_content)
    assert paths[2].check(exists=1, file=1)

    # Test
    expected = {str(paths[1]), str(paths[2])}

    def check_result(result, expected_existing):
        assert set(result) == expected
        assert result[paths[1]][0]['id'] == ids[1]
        assert result[paths[2]][0]['id'] == ids[2]
        assert [p.check(exists=1, file=1) for p in paths] == expected_existing

    result = api.check_files(ids=ids, directory=str(tmpdir))
    check_result(result, [True, True, True])

    result = api.check_files(paths=path_strings)
    check_result(result, [True, True, True])

    result = api.check_files(paths=path_strings, delete=True)
    check_result(result, [True, False, False])

    missing_file = str(tmpdir.join(smallest_archived_products[0]['title'] + '.zip'))
    result = api.check_files(paths=[missing_file])
    assert set(result) == {missing_file}
    assert result[missing_file][0]['id'] == smallest_archived_products[0]['id']

    with pytest.raises(ValueError):
        api.check_files(ids=ids)

    with pytest.raises(ValueError):
        api.check_files()

    tmpdir.remove()
