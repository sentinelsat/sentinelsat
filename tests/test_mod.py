import hashlib
import textwrap
from datetime import date, datetime, timedelta
from os import environ
import sys

import geojson
import py.path
import pytest
import requests
import requests_mock

from sentinelsat import InvalidChecksumError, SentinelAPI, SentinelAPIError, format_query_date, geojson_to_wkt, \
    read_geojson
from sentinelsat.sentinel import _format_order_by, _parse_odata_timestamp, _parse_opensearch_response
from .shared import FIXTURES_DIR, my_vcr

_api_auth = dict(user=environ.get('DHUS_USER'), password=environ.get('DHUS_PASSWORD'))

_api_kwargs = dict(_api_auth, api_url='https://scihub.copernicus.eu/apihub/')

_small_query = dict(
    area='POLYGON((0 0,1 1,0 1,0 0))',
    date=(datetime(2015, 1, 1), datetime(2015, 1, 2)))

_large_query = dict(
    area='POLYGON((0 0,0 10,10 10,10 0,0 0))',
    date=(datetime(2015, 12, 1), datetime(2015, 12, 31)))


@pytest.fixture(scope='session')
@my_vcr.use_cassette('products_fixture', decode_compressed_response=False)
def products():
    """A fixture for tests that need some non-specific set of products as input."""
    api = SentinelAPI(**_api_auth)
    products = api.query(
        geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map.geojson')),
        ("20151219", "20151228")
    )
    return products


@pytest.fixture(scope='session')
@my_vcr.use_cassette('products_fixture')
def raw_products():
    """A fixture for tests that need some non-specific set of products in the form of a raw response as input."""
    api = SentinelAPI(**_api_auth)
    raw_products = api._load_query(api.format_query(
        geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map.geojson')),
        ("20151219", "20151228"))
    )[0]
    return raw_products


@pytest.mark.fast
def test_format_date():
    assert format_query_date(datetime(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_query_date(date(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_query_date('2015-01-01T00:00:00Z') == '2015-01-01T00:00:00Z'
    assert format_query_date('20150101') == '2015-01-01T00:00:00Z'

    for date_str in ("NOW", "NOW-1DAY", "NOW-1DAYS", "NOW-500DAY", "NOW-500DAYS",
                     "NOW-2MONTH", "NOW-2MONTHS", "NOW-20MINUTE", "NOW-20MINUTES",
                     "NOW+10HOUR", "2015-01-01T00:00:00Z+1DAY"):
        assert format_query_date(date_str) == date_str

    for date_str in ("NOW - 1HOUR", "NOW -   1HOURS", "NOW-1 HOURS", "NOW-1", "NOW-"):
        with pytest.raises(ValueError) as excinfo:
            format_query_date(date_str)


@pytest.mark.fast
def test_format_date():
    assert format_query_date(datetime(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_query_date(date(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_query_date('2015-01-01T00:00:00Z') == '2015-01-01T00:00:00Z'
    assert format_query_date('20150101') == '2015-01-01T00:00:00Z'

    for date_str in ("NOW", "NOW-1DAY", "NOW-1DAYS", "NOW-500DAY", "NOW-500DAYS",
                     "NOW-2MONTH", "NOW-2MONTHS", "NOW-20MINUTE", "NOW-20MINUTES",
                     "NOW+10HOUR", "2015-01-01T00:00:00Z+1DAY", "NOW+3MONTHS-7DAYS/DAYS"):
        assert format_query_date(date_str) == date_str

    for date_str in ("NOW - 1HOUR", "NOW -   1HOURS", "NOW-1 HOURS", "NOW-1", "NOW-"):
        with pytest.raises(ValueError) as excinfo:
            format_query_date(date_str)


@pytest.mark.fast
def test_convert_timestamp():
    assert _parse_odata_timestamp('/Date(1445588544652)/') == datetime(2015, 10, 23, 8, 22, 24,
                                                                       652000)


@pytest.mark.fast
def test_progressbars(capsys):
    api = SentinelAPI("mock_user", "mock_password")
    testfile_md5 = hashlib.md5()
    true_path = FIXTURES_DIR + "/expected_search_footprints_s1.geojson"
    with open(true_path, "rb") as testfile:
        testfile_md5.update(testfile.read())
        real_md5 = testfile_md5.hexdigest()

    assert api._md5_compare(true_path, real_md5) is True
    out, err = capsys.readouterr()
    assert "checksumming" in err
    api = SentinelAPI("mock_user", "mock_password", show_progressbars=False)
    assert api._md5_compare(FIXTURES_DIR + "/map.geojson", real_md5) is False
    out, err = capsys.readouterr()
    assert out == ""
    assert "checksumming" not in err


@my_vcr.use_cassette
@pytest.mark.scihub
def test_SentinelAPI_connection():
    api = SentinelAPI(**_api_auth)
    api.query(**_small_query)

    assert api._last_query == (
        'beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z] '
        'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"')
    assert api._last_response.status_code == 200


@my_vcr.use_cassette
@pytest.mark.scihub
def test_SentinelAPI_wrong_credentials():
    api = SentinelAPI(
        "wrong_user",
        "wrong_password"
    )
    with pytest.raises(SentinelAPIError) as excinfo:
        api.query(**_small_query)
    assert excinfo.value.response.status_code == 401

    with pytest.raises(SentinelAPIError) as excinfo:
        api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
    assert excinfo.value.response.status_code == 401

    with pytest.raises(SentinelAPIError) as excinfo:
        api.download('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
    assert excinfo.value.response.status_code == 401

    with pytest.raises(SentinelAPIError) as excinfo:
        api.download_all(['8df46c9e-a20c-43db-a19a-4240c2ed3b8b'])
    assert excinfo.value.response.status_code == 401


@my_vcr.use_cassette
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
def test_api_query_format_ranges():
    query = SentinelAPI.format_query(cloudcoverpercentage=(0, 30))
    assert query == 'cloudcoverpercentage:[0 TO 30]'

    query = SentinelAPI.format_query(cloudcoverpercentage=[0, 30])
    assert query == 'cloudcoverpercentage:[0 TO 30]'

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

    with pytest.raises(ValueError):
        SentinelAPI.format_query(date="NOW")

    with pytest.raises(ValueError):
        SentinelAPI.format_query(date=["NOW"])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(ingestiondate=[])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(ingestiondate=[None, 'NOW'])


@my_vcr.use_cassette
@pytest.mark.scihub
def test_invalid_query():
    api = SentinelAPI(**_api_auth)
    with pytest.raises(SentinelAPIError) as excinfo:
        api.query(raw="xxx:yyy")


@pytest.mark.fast
def test_format_url():
    api = SentinelAPI(**_api_auth)
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

    with pytest.raises(ValueError) as excinfo:
        _format_order_by("+cloudcoverpercentage-beginposition")


@my_vcr.use_cassette
@pytest.mark.scihub
def test_small_query():
    api = SentinelAPI(**_api_kwargs)
    api.query(**_small_query)
    assert api._last_query == (
        'beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z] '
        'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"')
    assert api._last_response.status_code == 200


@my_vcr.use_cassette(decode_compressed_response=False)
@pytest.mark.scihub
def test_large_query():
    api = SentinelAPI(**_api_kwargs)
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


@my_vcr.use_cassette
@pytest.mark.scihub
def test_count():
    api = SentinelAPI(**_api_kwargs)
    count = api.count(None, ("20150101", "20151231"))
    assert count > 100000


@my_vcr.use_cassette
@pytest.mark.scihub
def test_too_long_query():
    api = SentinelAPI(**_api_kwargs)

    # Test whether our limit calculation is reasonably correct and
    # that a relevant error message is provided

    def create_query(n):
        return api.format_query(date=("NOW", "NOW"), raw=" abc_:*.+*~!," * n)

    # Expect no error
    q = create_query(170)
    assert 0.99 < SentinelAPI.check_query_length(q) < 1.0
    with pytest.raises(SentinelAPIError) as excinfo:
        api.query(raw=q)
    assert "Invalid query string" in excinfo.value.msg

    # Expect HTTP status 500 Internal Server Error
    q = create_query(171)
    assert 1.0 <= SentinelAPI.check_query_length(q) < 1.01
    with pytest.raises(SentinelAPIError) as excinfo:
        api.query(raw=q)
    assert excinfo.value.response.status_code == 500
    assert ("Request Entity Too Large" in excinfo.value.msg or
            "Request-URI Too Long" in excinfo.value.msg)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_date_arithmetic():
    api = SentinelAPI(**_api_kwargs)
    products = api.query('ENVELOPE(0, 10, 10, 0)',
                         ('2016-12-01T00:00:00Z-1DAY',
                          '2016-12-01T00:00:00Z+1DAY-1HOUR'))
    assert api._last_response.status_code == 200
    assert len(products) > 0


@my_vcr.use_cassette
@pytest.mark.scihub
def test_quote_symbol_bug():
    # A test to check if plus symbol handling works correctly on the server side
    # It used to raise an error but has since been fixed
    # https://github.com/SentinelDataHub/DataHubSystem/issues/23
    api = SentinelAPI(**_api_kwargs)

    q = 'beginposition:[2017-05-30T00:00:00Z TO 2017-05-31T00:00:00Z+1DAY]'
    count = api.count(raw=q)
    assert count > 0


@pytest.mark.fast
def test_get_coordinates():
    wkt = ('POLYGON((-66.2695 -8.0592,-66.2695 0.7031,'
           '-57.3047 0.7031,-57.3047 -8.0592,-66.2695 -8.0592))')
    assert geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map.geojson')) == wkt
    assert geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map_z.geojson')) == wkt


@my_vcr.use_cassette
@pytest.mark.scihub
def test_get_product_odata_short():
    api = SentinelAPI(**_api_auth)

    expected_short = {
        '8df46c9e-a20c-43db-a19a-4240c2ed3b8b': {
            'id': '8df46c9e-a20c-43db-a19a-4240c2ed3b8b',
            'size': 143549851,
            'md5': 'D5E4DF5C38C6E97BF7E7BD540AB21C05',
            'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
            'date': datetime(2015, 11, 21, 10, 3, 56, 675000),
            'footprint': 'POLYGON((-63.852531 -5.880887,-67.495872 -5.075419,-67.066071 -3.084356,-63.430576 -3.880541,'
                         '-63.852531 -5.880887))',
            'title': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC'
        },
        '44517f66-9845-4792-a988-b5ae6e81fd3e': {
            'id': '44517f66-9845-4792-a988-b5ae6e81fd3e',
            'date': datetime(2015, 12, 27, 14, 22, 29),
            'footprint': 'POLYGON((-58.80274769505742 -4.565257232533263,-58.80535376268811 -5.513960396525286,'
                         '-57.90315169909761 -5.515947033626909,-57.903151791669515 -5.516014389089381,-57.85874693129081 -5.516044812342758,'
                         '-57.814323596961835 -5.516142631941845,-57.81432351345917 -5.516075248310466,-57.00018056571297 -5.516633044843839,'
                         '-57.000180565731384 -5.516700066819259,-56.95603179187787 -5.51666329264377,-56.91188395837315 -5.516693539799448,'
                         '-56.91188396736038 -5.51662651925904,-56.097209386295305 -5.515947927683427,-56.09720929423562 -5.516014937246069,'
                         '-56.053056977999596 -5.5159111504805916,-56.00892491028779 -5.515874390220655,-56.00892501130261 -5.515807411549814,'
                         '-55.10621586418906 -5.513685455771881,-55.108821882251775 -4.6092845892233,-54.20840287327946 -4.606372862374043,'
                         '-54.21169990975238 -3.658594390979672,-54.214267703869346 -2.710949551849636,-55.15704255065496 -2.7127451087194463,'
                         '-56.0563616875051 -2.71378646425769,-56.9561852630143 -2.7141556791285275,-57.8999998009875 -2.713837142510183,'
                         '-57.90079161941062 -3.6180222056692726,-58.800616247288836 -3.616721351843382,-58.80274769505742 -4.565257232533263))',
            'md5': '48C5648C2644CE07207B3C943DEDEB44',
            'size': 5854429622,
            'title': 'S2A_OPER_PRD_MSIL1C_PDMC_20151228T112523_R110_V20151227T142229_20151227T142229',
            'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('44517f66-9845-4792-a988-b5ae6e81fd3e')/$value"
        }
    }
    for id, expected in expected_short.items():
        ret = api.get_product_odata(id)
        assert set(ret) == set(expected)
        for k in ret:
            assert ret[k] == expected[k]


@my_vcr.use_cassette
@pytest.mark.scihub
def test_get_product_odata_full():
    api = SentinelAPI(**_api_auth)

    expected_full = {
        '8df46c9e-a20c-43db-a19a-4240c2ed3b8b': {
            'id': '8df46c9e-a20c-43db-a19a-4240c2ed3b8b',
            'title': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC',
            'size': 143549851,
            'md5': 'D5E4DF5C38C6E97BF7E7BD540AB21C05',
            'date': datetime(2015, 11, 21, 10, 3, 56, 675000),
            'footprint': 'POLYGON((-63.852531 -5.880887,-67.495872 -5.075419,-67.066071 -3.084356,-63.430576 -3.880541,-63.852531 -5.880887))',
            'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')/$value",
            'Acquisition Type': 'NOMINAL',
            'Carrier rocket': 'Soyuz',
            'Cycle number': 64,
            'Date': datetime(2015, 11, 21, 10, 3, 56, 675000),
            'Filename': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC.SAFE',
            'Footprint': '<gml:Polygon srsName="http://www.opengis.net/gml/srs/epsg.xml#4326" xmlns:gml="http://www.opengis.net/gml">   <gml:outerBoundaryIs>      <gml:LinearRing>         <gml:coordinates>-5.880887,-63.852531 -5.075419,-67.495872 -3.084356,-67.066071 -3.880541,-63.430576 -5.880887,-63.852531</gml:coordinates>      </gml:LinearRing>   </gml:outerBoundaryIs></gml:Polygon>',
            'Format': 'SAFE',
            'Identifier': 'S1A_EW_GRDM_1SDV_20151121T100356_20151121T100429_008701_00C622_A0EC',
            'Ingestion Date': datetime(2015, 11, 21, 13, 22, 4, 992000),
            'Instrument': 'SAR-C',
            'Instrument abbreviation': 'SAR-C SAR',
            'Instrument description': '<a target="_blank" href="https://sentinel.esa.int/web/sentinel/missions/sentinel-1">https://sentinel.esa.int/web/sentinel/missions/sentinel-1</a>',
            'Instrument description text': 'The SAR Antenna Subsystem (SAS) is developed and build by AstriumGmbH. It is a large foldable planar phased array antenna, which isformed by a centre panel and two antenna side wings. In deployedconfiguration the antenna has an overall aperture of 12.3 x 0.84 m.The antenna provides a fast electronic scanning capability inazimuth and elevation and is based on low loss and highly stablewaveguide radiators build in carbon fibre technology, which arealready successfully used by the TerraSAR-X radar imaging mission.The SAR Electronic Subsystem (SES) is developed and build byAstrium Ltd. It provides all radar control, IF/ RF signalgeneration and receive data handling functions for the SARInstrument. The fully redundant SES is based on a channelisedarchitecture with one transmit and two receive chains, providing amodular approach to the generation and reception of wide-bandsignals and the handling of multi-polarisation modes. One keyfeature is the implementation of the Flexible Dynamic BlockAdaptive Quantisation (FD-BAQ) data compression concept, whichallows an efficient use of on-board storage resources and minimisesdownlink times.',
            'Instrument mode': 'EW',
            'Instrument name': 'Synthetic Aperture Radar (C-band)',
            'Instrument swath': 'EW',
            'JTS footprint': 'POLYGON ((-63.852531 -5.880887,-67.495872 -5.075419,-67.066071 -3.084356,-63.430576 -3.880541,-63.852531 -5.880887))',
            'Launch date': 'April 3rd, 2014',
            'Mission datatake id': 50722,
            'Mission type': 'Earth observation',
            'Mode': 'EW',
            'NSSDC identifier': '0000-000A',
            'Operator': 'European Space Agency',
            'Orbit number (start)': 8701,
            'Orbit number (stop)': 8701,
            'Pass direction': 'DESCENDING',
            'Phase identifier': 1,
            'Polarisation': 'VV VH',
            'Product class': 'S',
            'Product class description': 'SAR Standard L1 Product',
            'Product composition': 'Slice',
            'Product level': 'L1',
            'Product type': 'GRD',
            'Relative orbit (start)': 54, 'Relative orbit (stop)': 54, 'Resolution': 'Medium',
            'Satellite': 'Sentinel-1',
            'Satellite description': '<a target="_blank" href="https://sentinel.esa.int/web/sentinel/missions/sentinel-1">https://sentinel.esa.int/web/sentinel/missions/sentinel-1</a>',
            'Satellite name': 'Sentinel-1',
            'Satellite number': 'A',
            'Sensing start': datetime(2015, 11, 21, 10, 3, 56, 675000),
            'Sensing stop': datetime(2015, 11, 21, 10, 4, 29, 714000),
            'Size': '223.88 MB',
            'Slice number': 1,
            'Start relative orbit number': 54,
            'Status': 'ARCHIVED',
            'Stop relative orbit number': 54,
            'Timeliness Category': 'Fast-24h'
        },
        '44517f66-9845-4792-a988-b5ae6e81fd3e': {
            'id': '44517f66-9845-4792-a988-b5ae6e81fd3e',
            'title': 'S2A_OPER_PRD_MSIL1C_PDMC_20151228T112523_R110_V20151227T142229_20151227T142229',
            'size': 5854429622,
            'md5': '48C5648C2644CE07207B3C943DEDEB44',
            'date': datetime(2015, 12, 27, 14, 22, 29),
            'footprint': 'POLYGON((-58.80274769505742 -4.565257232533263,-58.80535376268811 -5.513960396525286,-57.90315169909761 -5.515947033626909,-57.903151791669515 -5.516014389089381,-57.85874693129081 -5.516044812342758,-57.814323596961835 -5.516142631941845,-57.81432351345917 -5.516075248310466,-57.00018056571297 -5.516633044843839,-57.000180565731384 -5.516700066819259,-56.95603179187787 -5.51666329264377,-56.91188395837315 -5.516693539799448,-56.91188396736038 -5.51662651925904,-56.097209386295305 -5.515947927683427,-56.09720929423562 -5.516014937246069,-56.053056977999596 -5.5159111504805916,-56.00892491028779 -5.515874390220655,-56.00892501130261 -5.515807411549814,-55.10621586418906 -5.513685455771881,-55.108821882251775 -4.6092845892233,-54.20840287327946 -4.606372862374043,-54.21169990975238 -3.658594390979672,-54.214267703869346 -2.710949551849636,-55.15704255065496 -2.7127451087194463,-56.0563616875051 -2.71378646425769,-56.9561852630143 -2.7141556791285275,-57.8999998009875 -2.713837142510183,-57.90079161941062 -3.6180222056692726,-58.800616247288836 -3.616721351843382,-58.80274769505742 -4.565257232533263))',
            'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('44517f66-9845-4792-a988-b5ae6e81fd3e')/$value",
            'Cloud cover percentage': 18.153846153846153,
            'Date': datetime(2015, 12, 27, 14, 22, 29),
            'Degraded MSI data percentage': 0, 'Degraded ancillary data percentage': 0,
            'Filename': 'S2A_OPER_PRD_MSIL1C_PDMC_20151228T112523_R110_V20151227T142229_20151227T142229.SAFE',
            'Footprint': '<gml:Polygon srsName="http://www.opengis.net/gml/srs/epsg.xml#4326" xmlns:gml="http://www.opengis.net/gml">   <gml:outerBoundaryIs>      <gml:LinearRing>         <gml:coordinates>-4.565257232533263,-58.80274769505742 -5.513960396525286,-58.80535376268811 -5.515947033626909,-57.90315169909761 -5.516014389089381,-57.903151791669515 -5.516044812342758,-57.85874693129081 -5.516142631941845,-57.814323596961835 -5.516075248310466,-57.81432351345917 -5.516633044843839,-57.00018056571297 -5.516700066819259,-57.000180565731384 -5.51666329264377,-56.95603179187787 -5.516693539799448,-56.91188395837315 -5.51662651925904,-56.91188396736038 -5.515947927683427,-56.097209386295305 -5.516014937246069,-56.09720929423562 -5.5159111504805916,-56.053056977999596 -5.515874390220655,-56.00892491028779 -5.515807411549814,-56.00892501130261 -5.513685455771881,-55.10621586418906 -4.6092845892233,-55.108821882251775 -4.606372862374043,-54.20840287327946 -3.658594390979672,-54.21169990975238 -2.710949551849636,-54.214267703869346 -2.7127451087194463,-55.15704255065496 -2.71378646425769,-56.0563616875051 -2.7141556791285275,-56.9561852630143 -2.713837142510183,-57.8999998009875 -3.6180222056692726,-57.90079161941062 -3.616721351843382,-58.800616247288836 -4.565257232533263,-58.80274769505742</gml:coordinates>      </gml:LinearRing>   </gml:outerBoundaryIs></gml:Polygon>',
            'Format': 'SAFE',
            'Format correctness': 'PASSED',
            'General quality': 'PASSED',
            'Generation time': datetime(2015, 12, 28, 11, 25, 23, 357),
            'Geometric quality': 'PASSED',
            'Identifier': 'S2A_OPER_PRD_MSIL1C_PDMC_20151228T112523_R110_V20151227T142229_20151227T142229',
            'Ingestion Date': datetime(2015, 12, 28, 10, 57, 13, 725000),
            'Instrument': 'MSI',
            'Instrument abbreviation': 'MSI',
            'Instrument mode': 'INS-NOBS',
            'Instrument name': 'Multi-Spectral Instrument',
            'JTS footprint': 'POLYGON ((-58.80274769505742 -4.565257232533263,-58.80535376268811 -5.513960396525286,-57.90315169909761 -5.515947033626909,-57.903151791669515 -5.516014389089381,-57.85874693129081 -5.516044812342758,-57.814323596961835 -5.516142631941845,-57.81432351345917 -5.516075248310466,-57.00018056571297 -5.516633044843839,-57.000180565731384 -5.516700066819259,-56.95603179187787 -5.51666329264377,-56.91188395837315 -5.516693539799448,-56.91188396736038 -5.51662651925904,-56.097209386295305 -5.515947927683427,-56.09720929423562 -5.516014937246069,-56.053056977999596 -5.5159111504805916,-56.00892491028779 -5.515874390220655,-56.00892501130261 -5.515807411549814,-55.10621586418906 -5.513685455771881,-55.108821882251775 -4.6092845892233,-54.20840287327946 -4.606372862374043,-54.21169990975238 -3.658594390979672,-54.214267703869346 -2.710949551849636,-55.15704255065496 -2.7127451087194463,-56.0563616875051 -2.71378646425769,-56.9561852630143 -2.7141556791285275,-57.8999998009875 -2.713837142510183,-57.90079161941062 -3.6180222056692726,-58.800616247288836 -3.616721351843382,-58.80274769505742 -4.565257232533263))',
            'Mission datatake id': 'GS2A_20151227T140932_002681_N02.01',
            'NSSDC identifier': '2015-000A',
            'Orbit number (start)': 2681,
            'Pass direction': 'DESCENDING',
            'Platform serial identifier': 'Sentinel-2A',
            'Processing baseline': 2.01,
            'Processing level': 'Level-1C',
            'Product type': 'S2MSI1C',
            'Radiometric quality': 'PASSED',
            'Relative orbit (start)': 110,
            'Satellite': 'Sentinel-2',
            'Satellite name': 'Sentinel-2',
            'Satellite number': 'A',
            'Sensing start': datetime(2015, 12, 27, 14, 22, 29),
            'Sensing stop': datetime(2015, 12, 27, 14, 22, 29),
            'Sensor quality': 'PASSED',
            'Size': '5.50 GB'
        }
    }
    for id, expected in expected_full.items():
        ret = api.get_product_odata(id, full=True)
        assert set(ret) == set(expected)
        for k in ret:
            assert ret[k] == expected[k]


@my_vcr.use_cassette
@pytest.mark.scihub
def test_get_product_info_bad_key():
    api = SentinelAPI(**_api_auth)

    with pytest.raises(SentinelAPIError) as excinfo:
        api.get_product_odata('invalid-xyz')
    assert excinfo.value.msg == "InvalidKeyException : Invalid key (invalid-xyz) to access Products"


@pytest.mark.mock_api
def test_get_product_odata_scihub_down():
    api = SentinelAPI("mock_user", "mock_password")

    request_url = "https://scihub.copernicus.eu/apihub/odata/v1/Products('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')?$format=json"

    with requests_mock.mock() as rqst:
        rqst.get(
            request_url,
            text="Mock SciHub is Down", status_code=503
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert excinfo.value.msg == "Mock SciHub is Down"

        rqst.get(
            request_url,
            text='{"error":{"code":null,"message":{"lang":"en","value":'
                 '"No Products found with key \'8df46c9e-a20c-43db-a19a-4240c2ed3b8b\' "}}}',
            status_code=500
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert excinfo.value.msg == "No Products found with key \'8df46c9e-a20c-43db-a19a-4240c2ed3b8b\' "

        rqst.get(
            request_url,
            text="Mock SciHub is Down", status_code=200
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert excinfo.value.msg == "Mock SciHub is Down"

        # Test with a real "server under maintenance" response
        rqst.get(
            request_url,
            text=textwrap.dedent("""\
            <!doctype html>
            <title>The Sentinels Scientific Data Hub</title>
            <link href='https://fonts.googleapis.com/css?family=Open+Sans' rel='stylesheet' type='text/css'>
            <style>
            body { text-align: center; padding: 125px; background: #fff;}
            h1 { font-size: 50px; }
            body { font: 20px 'Open Sans',Helvetica, sans-serif; color: #333; }
            article { display: block; text-align: left; width: 820px; margin: 0 auto; }
            a { color: #0062a4; text-decoration: none; font-size: 26px }
            a:hover { color: #1b99da; text-decoration: none; }
            </style>

            <article>
            <img alt="" src="/datahub.png" style="float: left;margin: 20px;">
            <h1>The Sentinels Scientific Data Hub will be back soon!</h1>
            <div style="margin-left: 145px;">
            <p>
            Sorry for the inconvenience,<br/>
            we're performing some maintenance at the moment.<br/>
            </p>
            <!--<p><a href="https://scihub.copernicus.eu/news/News00098">https://scihub.copernicus.eu/news/News00098</a></p>-->
            <p>
            We'll be back online shortly!
            </p>
            </div>
            </article>
            """),
            status_code=502)
        with pytest.raises(SentinelAPIError) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')
        assert "The Sentinels Scientific Data Hub will be back soon!" in excinfo.value.msg


@pytest.mark.mock_api
def test_scihub_unresponsive():
    api = SentinelAPI("mock_user", "mock_password")

    with requests_mock.mock() as rqst:
        rqst.request(requests_mock.ANY, requests_mock.ANY, exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(requests.exceptions.Timeout) as excinfo:
            api.query(**_small_query)

        with pytest.raises(requests.exceptions.Timeout) as excinfo:
            api.get_product_odata('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(requests.exceptions.Timeout) as excinfo:
            api.download('8df46c9e-a20c-43db-a19a-4240c2ed3b8b')

        with pytest.raises(requests.exceptions.Timeout) as excinfo:
            api.download_all(['8df46c9e-a20c-43db-a19a-4240c2ed3b8b'])


@pytest.mark.mock_api
def test_get_products_invalid_json():
    api = SentinelAPI("mock_user", "mock_password")
    with requests_mock.mock() as rqst:
        rqst.post(
            'https://scihub.copernicus.eu/apihub/search?format=json',
            text="{Invalid JSON response", status_code=200
        )
        with pytest.raises(SentinelAPIError) as excinfo:
            api.query(
                area=geojson_to_wkt(read_geojson(FIXTURES_DIR + "/map.geojson")),
                date=("20151219", "20151228"),
                platformname="Sentinel-2"
            )
        assert excinfo.value.msg == "Invalid API response."


@my_vcr.use_cassette
@pytest.mark.scihub
def test_footprints_s1():
    api = SentinelAPI(**_api_auth)
    products = api.query(
        geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map.geojson')),
        (datetime(2014, 10, 10), datetime(2014, 12, 31)), producttype="GRD"
    )

    footprints = api.to_geojson(products)
    for footprint in footprints['features']:
        assert not footprint['geometry'].errors()

    with open(FIXTURES_DIR + '/expected_search_footprints_s1.geojson') as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
    # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
    assert set(footprints) == set(expected_footprints)


@pytest.mark.scihub
def test_footprints_s2(products):
    footprints = SentinelAPI.to_geojson(products)
    for footprint in footprints['features']:
        assert not footprint['geometry'].errors()

    with open(FIXTURES_DIR + '/expected_search_footprints_s2.geojson') as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
    # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
    assert set(footprints) == set(expected_footprints)


@my_vcr.use_cassette
@pytest.mark.scihub
def test_s2_cloudcover():
    api = SentinelAPI(**_api_auth)
    products = api.query(
        geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map.geojson')),
        ("20151219", "20151228"),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 10)
    )
    assert len(products) == 3

    product_ids = list(products)
    assert product_ids[0] == "6ed0b7de-3435-43df-98bf-ad63c8d077ef"
    assert product_ids[1] == "37ecee60-23d8-4ec2-a65f-2de24f51d30e"
    assert product_ids[2] == "0848f6b8-5730-4759-850e-fc9945d42296"

    # For order-by test
    vals = [x["cloudcoverpercentage"] for x in products.values()]
    assert sorted(vals) != vals


@my_vcr.use_cassette
@pytest.mark.scihub
def test_order_by():
    api = SentinelAPI(**_api_auth)
    kwargs = dict(
        area=geojson_to_wkt(read_geojson(FIXTURES_DIR + '/map.geojson')),
        date=("20151219", "20161019"),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 10),
        order_by="cloudcoverpercentage, -beginposition"
    )
    # Check that order_by works correctly also in cases where pagination is required
    expected_count = api.count(**kwargs)
    assert expected_count > 100
    products = api.query(**kwargs)
    assert len(products) == expected_count
    vals = [x["cloudcoverpercentage"] for x in products.values()]
    assert sorted(vals) == vals


@my_vcr.use_cassette
@pytest.mark.scihub
def test_area_relation():
    api = SentinelAPI(**_api_auth)
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
    with pytest.raises(ValueError) as excinfo:
        api.query(area_relation="disjoint", **params)


@pytest.mark.scihub
def test_get_products_size(products):
    assert SentinelAPI.get_products_size(products) == 90.94

    # load a new very small query
    api = SentinelAPI(**_api_auth)
    with my_vcr.use_cassette('test_get_products_size'):
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
    assert '44517f66-9845-4792-a988-b5ae6e81fd3e' in dictionary
    props = dictionary['44517f66-9845-4792-a988-b5ae6e81fd3e']
    expected_title = 'S2A_OPER_PRD_MSIL1C_PDMC_20151228T112523_R110_V20151227T142229_20151227T142229'
    assert props['title'] == expected_title


@pytest.mark.fast
@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.skipif(sys.version_info <= (3,4),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_missing_dependency_dataframe(monkeypatch):
    api = SentinelAPI("mock_user", "mock_password")

    with pytest.raises(ImportError):
        monkeypatch.setitem(sys.modules, "pandas", None)                
        api.to_dataframe({"test":"test"})

    with pytest.raises(ImportError):
        monkeypatch.setitem(sys.modules, "geopandas", None)
        api.to_geodataframe({"test":"tst"})


@pytest.mark.pandas
@pytest.mark.scihub
@pytest.mark.skipif(sys.version_info < (3,5),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_to_pandas(products):
    df = SentinelAPI.to_dataframe(products)
    assert '44517f66-9845-4792-a988-b5ae6e81fd3e' in df.index


@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.scihub
@pytest.mark.skipif(sys.version_info < (3,5),
                    reason="Pandas requires Python 2.7 or >=3.5")
def test_to_geopandas(products):
    gdf = SentinelAPI.to_geodataframe(products)
    assert abs(gdf.unary_union.area - 132.16) < 0.01


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download(tmpdir):
    api = SentinelAPI(**_api_auth)
    uuid = "1f62a176-c980-41dc-b3a1-c735d660c910"
    filename = "S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E"
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


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_all(tmpdir):
    api = SentinelAPI(**_api_auth)
    # From https://scihub.copernicus.eu/apihub/odata/v1/Products?$top=5&$orderby=ContentLength
    # filenames = ["S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E",
    #              "S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A",
    #              "S1A_WV_OCN__2SSV_20150526T081641_20150526T082418_006090_007E3E_104C"]

    # Corresponding IDs
    ids = [
        "5618ce1b-923b-4df2-81d9-50b53e5aded9",
        "d8340134-878f-4891-ba4f-4df54f1e3ab4",
        "1f62a176-c980-41dc-b3a1-c735d660c910"
    ]

    # Download normally
    product_infos, failed_downloads = api.download_all(ids, str(tmpdir))
    assert len(failed_downloads) == 0
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
        product_infos, failed_downloads = api.download_all(
            ids, str(tmpdir), max_attempts=1, checksum=True)
        assert len(failed_downloads) == 1
        assert len(product_infos) + len(failed_downloads) == len(ids)
        assert id in failed_downloads

    tmpdir.remove()


@my_vcr.use_cassette
@pytest.mark.scihub
def test_download_invalid_id():
    api = SentinelAPI(**_api_auth)
    uuid = "1f62a176-c980-41dc-xxxx-c735d660c910"
    with pytest.raises(SentinelAPIError) as excinfo:
        api.download(uuid)
        assert 'Invalid key' in excinfo.value.msg


@my_vcr.use_cassette
@pytest.mark.scihub
def test_query_by_names():
    api = SentinelAPI(**_api_auth)
    names = ["S2A_MSIL1C_20170205T105221_N0204_R051_T31TCF_20170205T105426",
             "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1"]
    expected = {names[0]: {"2f379a52-3041-4b92-a8a8-92bddc495594"},
                names[1]: {"2d116e6a-536e-49b3-a587-5cd6b5baa3c9"}}

    result = api._query_names(names)
    assert list(result) == names
    for name in names:
        assert set(result[name]) == expected[name]

    result2 = api._query_names(names * 100)
    assert result == result2


@my_vcr.use_cassette
@pytest.mark.scihub
def test_check_existing(tmpdir):
    api = SentinelAPI(**_api_auth)
    ids = [
        "5618ce1b-923b-4df2-81d9-50b53e5aded9",
        "d8340134-878f-4891-ba4f-4df54f1e3ab4",
        "1f62a176-c980-41dc-b3a1-c735d660c910"
    ]
    names = ["S1A_WV_OCN__2SSV_20150526T081641_20150526T082418_006090_007E3E_104C",
             "S1A_WV_OCN__2SSV_20150526T211029_20150526T211737_006097_007E78_134A",
             "S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E"]
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
        f.write(b'\0')
    # File #3: incomplete
    dummy_content = b'aaaaaaaaaaaaaaaaaaaaaaaaa'
    with paths[2].open("wb") as f:
        f.write(dummy_content)
    assert paths[2].check(exists=1, file=1)

    # Test
    expected = {str(paths[1]), str(paths[2])}

    result = api.check_files(ids=ids, directory=str(tmpdir))
    assert set(result) == expected
    assert result[paths[1]][0]['id'] == ids[1]
    assert result[paths[2]][0]['id'] == ids[2]
    assert paths[0].check(exists=1, file=1)
    assert paths[1].check(exists=1, file=1)
    assert paths[2].check(exists=1, file=1)

    result = api.check_files(paths=path_strings)
    assert set(result) == expected
    assert result[paths[1]][0]['id'] == ids[1]
    assert result[paths[2]][0]['id'] == ids[2]
    assert paths[0].check(exists=1, file=1)
    assert paths[1].check(exists=1, file=1)
    assert paths[2].check(exists=1, file=1)

    result = api.check_files(paths=path_strings, delete=True)
    assert set(result) == expected
    assert result[paths[1]][0]['id'] == ids[1]
    assert result[paths[2]][0]['id'] == ids[2]
    assert paths[0].check(exists=1, file=1)
    assert not paths[1].check(exists=1, file=1)
    assert not paths[2].check(exists=1, file=1)

    missing_file = str(tmpdir.join(
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.zip"))
    result = api.check_files(paths=[missing_file])
    assert set(result) == {missing_file}
    assert result[missing_file][0]['id']

    with pytest.raises(ValueError):
        api.check_files(ids=ids)

    with pytest.raises(ValueError):
        api.check_files()

    tmpdir.remove()
