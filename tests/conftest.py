import re
import threading
from datetime import datetime
from functools import reduce
from os import environ
from os.path import abspath, dirname, exists, isfile, join

import pytest
import yaml
from pytest_socket import disable_socket
from vcr import VCR

import sentinelsat
from sentinelsat import SentinelAPI, geojson_to_wkt, read_geojson
from .custom_serializer import BinaryContentSerializer

TESTS_DIR = dirname(abspath(__file__))
FIXTURES_DIR = join(TESTS_DIR, "fixtures")
CASSETTE_DIR = join(FIXTURES_DIR, "vcr_cassettes")


def pytest_runtest_setup(item):
    markers = {mark.name for mark in item.iter_markers()}
    if "pandas" in markers:
        pytest.importorskip("pandas")
    if "geopandas" in markers:
        pytest.importorskip("geopandas")

    if not markers.intersection({"scihub", "fast", "mock_api"}):
        pytest.fail("The test is missing a 'scihub', 'fast' or 'mock_api' marker")


def scrub_request(request):
    for header in ("Authorization", "Set-Cookie", "Cookie"):
        if header in request.headers:
            del request.headers[header]
    return request


def scrub_response(response):
    ignore = {
        x.lower()
        for x in [
            "Authorization",
            "Set-Cookie",
            "Cookie",
            "Date",
            "Expires",
            "Transfer-Encoding",
            "last-modified",
        ]
    }
    for header in list(response["headers"]):
        if (
            header.lower() in ignore
            or header.lower().startswith("access-control")
            or header.lower().startswith("x-")
        ):
            del response["headers"][header]
    return response


def scrub_string(string, replacement=b""):
    """Scrub a string from a VCR response body string"""

    def before_record_response(response):
        len_before = len(response["body"]["string"])
        response["body"]["string"] = re.sub(string, replacement, response["body"]["string"])
        len_diff = len(response["body"]["string"]) - len_before
        if "content-length" in response["headers"]:
            response["headers"]["content-length"] = [
                str(int(response["headers"]["content-length"][0]) + len_diff)
            ]
        return response

    return before_record_response


def chain(*funcs):
    def chained_call(arg):
        return reduce(lambda x, f: f(x), funcs, arg)

    return chained_call


# Configure pytest-vcr
@pytest.fixture(scope="module")
def vcr(vcr):
    def range_header_matcher(r1, r2):
        return r1.headers.get("Range", "") == r2.headers.get("Range", "")

    vcr.cassette_library_dir = CASSETTE_DIR
    vcr.path_transformer = VCR.ensure_suffix(".yaml")
    vcr.filter_headers = ["Set-Cookie"]
    vcr.before_record_request = scrub_request
    vcr.before_record_response = chain(
        scrub_response,
        scrub_string(rb"Request done in \S+ seconds.", b"Request done in ... seconds."),
        scrub_string(rb'"updated":"[^"]+"', b'"updated":"..."'),
        scrub_string(rb'totalResults":"\d{4,}"', b'totalResults":"10000"'),
        scrub_string(rb"of \d{4,} total results", b"of 10000 total results"),
        scrub_string(rb"&start=\d{4,}&rows=0", b"&start=10000&rows=0"),
    )
    vcr.decode_compressed_response = True
    vcr.register_serializer("custom", BinaryContentSerializer(CASSETTE_DIR))
    vcr.serializer = "custom"
    vcr.register_matcher("range_header", range_header_matcher)
    vcr.match_on = ["method", "range_header", "host", "port", "path", "query", "body"]
    return vcr


@pytest.fixture(scope="session")
def credentials(request):
    # local tests require environment variables `DHUS_USER` and `DHUS_PASSWORD`
    # for Travis CI they are set as encrypted environment variables and stored
    record_mode = request.config.getoption("--vcr-record")
    disable_vcr = request.config.getoption("--disable-vcr")
    if record_mode in ["none", None] and not disable_vcr:
        # Using VCR.py cassettes for pre-recorded query playback
        # Any network traffic will raise an exception
        disable_socket()
    elif "DHUS_USER" not in environ or "DHUS_PASSWORD" not in environ:
        raise ValueError(
            "Credentials must be set when --vcr-record is not none or --disable-vcr is used. "
            "Please set DHUS_USER and DHUS_PASSWORD environment variables."
        )

    return [environ.get("DHUS_USER"), environ.get("DHUS_PASSWORD")]


@pytest.fixture(scope="session")
def api_kwargs(credentials):
    user, password = credentials
    return dict(user=user, password=password, api_url="https://apihub.copernicus.eu/apihub/")


@pytest.fixture
def api(api_kwargs):
    return SentinelAPI(**api_kwargs)


@pytest.fixture(scope="session")
def fixture_path():
    return lambda filename: join(FIXTURES_DIR, filename)


@pytest.fixture(scope="session")
def read_fixture_file(fixture_path):
    def read_func(filename, mode="r"):
        with open(fixture_path(filename), mode) as f:
            return f.read()

    return read_func


@pytest.fixture(scope="session")
def read_yaml(fixture_path, read_fixture_file):
    def read_or_store(filename, result):
        path = fixture_path(filename)
        if not exists(path):
            # Store the expected result for future if the fixture file is missing
            with open(path, "w") as f:
                yaml.safe_dump(result, f)
        return yaml.safe_load(read_fixture_file(filename))

    return read_or_store


@pytest.fixture(scope="session")
def geojson_path():
    path = join(FIXTURES_DIR, "map.geojson")
    assert isfile(path)
    return path


@pytest.fixture(scope="session")
def geojson_string():
    string = """{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              -66.26953125,
              -8.05922962720018
            ],
            [
              -66.26953125,
              0.7031073524364909
            ],
            [
              -57.30468749999999,
              0.7031073524364909
            ],
            [
              -57.30468749999999,
              -8.05922962720018
            ],
            [
              -66.26953125,
              -8.05922962720018
            ]
          ]
        ]
      }
    }
  ]
}"""
    return string


@pytest.fixture(scope="session")
def wkt_string():
    string = (
        "POLYGON((-78.046875 46.377254205100286,-75.76171874999999 43.32517767999295,-71.279296875 "
        "46.55886030311717,-78.046875 46.377254205100286))"
    )
    return string


@pytest.fixture(scope="session")
def test_wkt(geojson_path):
    return geojson_to_wkt(read_geojson(geojson_path))


@pytest.fixture(scope="module")
def products(api_kwargs, vcr, test_wkt):
    """A fixture for tests that need some non-specific set of products as input."""
    with vcr.use_cassette("products_fixture", decode_compressed_response=False):
        api = SentinelAPI(**api_kwargs)
        products = api.query(test_wkt, ("20151219", "20151228"))
    assert len(products) > 20
    return products


@pytest.fixture(scope="module")
def nbs_s3_response():
    """A fixture for tests of parsing response of a Sentinel-3 query of the Norwegian Ground Segment."""
    response_json = [
        {
            "title": "S3A_SL_1_RBT____20240202T194952_20240202T195252_20240204T052728_0179_108_299_1080_PS1_O_NT_004",
            "link": [
                {
                    "href": "https://colhub-archive.met.no/odata/v1/Products('562b62eb-a282-430a-9135-5d90fe5df45f')/$value"
                },
                {
                    "rel": "alternative",
                    "href": "https://colhub-archive.met.no/odata/v1/Products('562b62eb-a282-430a-9135-5d90fe5df45f')/",
                },
                {
                    "rel": "icon",
                    "href": "https://colhub-archive.met.no/odata/v1/Products('562b62eb-a282-430a-9135-5d90fe5df45f')/Products('Quicklook')/$value",
                },
            ],
            "id": "562b62eb-a282-430a-9135-5d90fe5df45f",
            "summary": "Date: 2024-02-02T19:49:51.707Z, Instrument: , Satellite: SENTINEL-3, Size: 377.70 MB",
            "ondemand": "false",
            "date": [
                {"name": "ingestiondate", "content": "2024-02-04T05:38:40.76Z"},
                {"name": "beginposition", "content": "2024-02-02T19:49:51.707Z"},
                {"name": "endposition", "content": "2024-02-02T19:52:51.707Z"},
            ],
            "int": [
                {"name": "orbitnumber", "content": "41467"},
                {"name": "relativeorbitnumber", "content": "299"},
            ],
            "str": [
                {
                    "name": "filename",
                    "content": "S3A_SL_1_RBT____20240202T194952_20240202T195252_20240204T052728_0179_108_299_1080_PS1_O_NT_004.SEN3",
                },
                {
                    "name": "gmlfootprint",
                    "content": "<gml:Polygon xmlns:gml='http://www.opengis.net/gml'>  <gml:outerBoundaryIs>    <gml:LinearRing>      <gml:coordinates>        70.1078,-8.62911 68.0448,-3.84106 65.8368,0.235547 63.5405,3.66802 61.1849,6.58432 61.1812,6.6096 61.2669,6.92122 61.4798,7.77118 61.6827,8.61851 61.8874,9.47528         62.0957,10.3596 62.2808,11.2423 62.4685,12.1521 62.655,13.0509 62.83,13.9771 62.9984,14.9076 63.1601,15.8468 63.3157,16.8006 63.466,17.7708 63.6099,18.7411         63.7468,19.7178 63.8773,20.7076 64.0021,21.7064 64.1213,22.7165 64.2324,23.7515 64.3329,24.7595 64.4249,25.8025 64.5152,26.8344 64.5998,27.8833 64.6617,28.9528         64.7303,30.0175 64.7861,31.0719 64.8385,32.1406 64.8858,33.2041 64.9154,34.279 64.9462,35.3556 64.9549,35.3545 67.5638,35.0529 70.1802,34.7773 72.7954,34.5399         75.3661,34.3624 75.356,32.5746 75.3195,30.7587 75.289,28.9487 75.2322,27.1687 75.1622,25.3945 75.0818,23.6595 74.9869,21.9303 74.8753,20.2295 74.7536,18.559         74.6245,16.8663 74.4826,15.2632 74.3236,13.6794 74.1551,12.0956 73.9757,10.5669 73.7861,9.08152 73.5875,7.62413 73.3791,6.19045 73.1595,4.78424 72.9315,3.42542         72.696,2.1038 72.4524,0.813489 72.1901,-0.432832 71.9325,-1.65117 71.6691,-2.83345 71.3931,-3.96768 71.1087,-5.11013 70.8179,-6.19399 70.5214,-7.22639 70.2222,-8.26082         70.1078,-8.62911       </gml:coordinates>    </gml:LinearRing>  </gml:outerBoundaryIs></gml:Polygon>",
                },
                {"name": "format"},
                {
                    "name": "identifier",
                    "content": "S3A_SL_1_RBT____20240202T194952_20240202T195252_20240204T052728_0179_108_299_1080_PS1_O_NT_004",
                },
                {"name": "sensoroperationalmode", "content": "Earth Observation"},
                {
                    "name": "footprint",
                    "content": "POLYGON ((-8.62911 70.1078, -3.84106 68.0448, 0.235547 65.8368, 3.66802 63.5405, 6.58432 61.1849, 6.6096 61.1812, 6.92122 61.2669, 7.77118 61.4798, 8.61851 61.6827, 9.47528 61.8874, 10.3596 62.0957, 11.2423 62.2808, 12.1521 62.4685, 13.0509 62.655, 13.9771 62.83, 14.9076 62.9984, 15.8468 63.1601, 16.8006 63.3157, 17.7708 63.466, 18.7411 63.6099, 19.7178 63.7468, 20.7076 63.8773, 21.7064 64.0021, 22.7165 64.1213, 23.7515 64.2324, 24.7595 64.3329, 25.8025 64.4249, 26.8344 64.5152, 27.8833 64.5998, 28.9528 64.6617, 30.0175 64.7303, 31.0719 64.7861, 32.1406 64.8385, 33.2041 64.8858, 34.279 64.9154, 35.3556 64.9462, 35.3545 64.9549, 35.0529 67.5638, 34.7773 70.1802, 34.5399 72.7954, 34.3624 75.3661, 32.5746 75.356, 30.7587 75.3195, 28.9487 75.289, 27.1687 75.2322, 25.3945 75.1622, 23.6595 75.0818, 21.9303 74.9869, 20.2295 74.8753, 18.559 74.7536, 16.8663 74.6245, 15.2632 74.4826, 13.6794 74.3236, 12.0956 74.1551, 10.5669 73.9757, 9.08152 73.7861, 7.62413 73.5875, 6.19045 73.3791, 4.78424 73.1595, 3.42542 72.9315, 2.1038 72.696, 0.813489 72.4524, -0.432832 72.1901, -1.65117 71.9325, -2.83345 71.6691, -3.96768 71.3931, -5.11013 71.1087, -6.19399 70.8179, -7.22639 70.5214, -8.26082 70.2222, -8.62911 70.1078))",
                },
                {"name": "producttype", "content": "SL_1_RBT___"},
                {"name": "platformname", "content": "SENTINEL-3"},
                {"name": "size", "content": "377.70 MB"},
                {"name": "timeliness", "content": "NT"},
                {"name": "orbitdirection", "content": "ASCENDING"},
                {"name": "processinglevel", "content": "1"},
                {"name": "uuid", "content": "562b62eb-a282-430a-9135-5d90fe5df45f"},
            ],
        },
        {
            "title": "S3A_SL_1_RBT____20240202T180852_20240202T181152_20240204T034253_0179_108_298_1080_PS1_O_NT_004",
            "link": [
                {
                    "href": "https://colhub-archive.met.no/odata/v1/Products('57897bfd-91a5-441f-a39b-a9159d9a410f')/$value"
                },
                {
                    "rel": "alternative",
                    "href": "https://colhub-archive.met.no/odata/v1/Products('57897bfd-91a5-441f-a39b-a9159d9a410f')/",
                },
                {
                    "rel": "icon",
                    "href": "https://colhub-archive.met.no/odata/v1/Products('57897bfd-91a5-441f-a39b-a9159d9a410f')/Products('Quicklook')/$value",
                },
            ],
            "id": "57897bfd-91a5-441f-a39b-a9159d9a410f",
            "summary": "Date: 2024-02-02T18:08:52.424Z, Instrument: , Satellite: SENTINEL-3, Size: 378.62 MB",
            "ondemand": "false",
            "date": [
                {"name": "ingestiondate", "content": "2024-02-04T03:55:31.657Z"},
                {"name": "beginposition", "content": "2024-02-02T18:08:52.424Z"},
                {"name": "endposition", "content": "2024-02-02T18:11:52.424Z"},
            ],
            "int": [
                {"name": "orbitnumber", "content": "41466"},
                {"name": "relativeorbitnumber", "content": "298"},
            ],
            "str": [
                {
                    "name": "filename",
                    "content": "S3A_SL_1_RBT____20240202T180852_20240202T181152_20240204T034253_0179_108_298_1080_PS1_O_NT_004.SEN3",
                },
                {
                    "name": "gmlfootprint",
                    "content": "<gml:Polygon xmlns:gml='http://www.opengis.net/gml'>  <gml:outerBoundaryIs>    <gml:LinearRing>      <gml:coordinates>        70.1098,16.6168 68.0469,21.4051 65.839,25.4819 63.5428,28.9145 61.1872,31.8309 61.1836,31.8562 61.2697,32.173 61.4834,33.0015 61.6886,33.872 61.8939,34.7351         62.092,35.6021 62.28,36.4883 62.4753,37.3905 62.6545,38.2995 62.8295,39.2264 62.9968,40.1581 63.1585,41.0982 63.3231,42.045 63.4733,43.0157 63.617,43.9862         63.7541,44.9638 63.8842,45.9522 64.0082,46.9765 64.1187,47.9718 64.2322,48.9817 64.3298,50.0184 64.4319,51.0473 64.5222,52.0811 64.5952,53.1515 64.6685,54.2045         64.733,55.2546 64.7927,56.3232 64.845,57.3918 64.8927,58.4526 64.9256,59.531 64.9481,60.6046 64.9568,60.6036 67.5657,60.3023 70.182,60.0271 72.7971,59.7903         75.3677,59.6135 75.3645,57.8034 75.3251,56.019 75.2949,54.208 75.2383,52.4261 75.1685,50.6494 75.0884,48.9112 74.9876,47.1653 74.8821,45.4774 74.7605,43.8062         74.629,42.1595 74.4821,40.5075 74.3229,38.9256 74.162,37.338 73.9826,35.8086 73.793,34.3222 73.5943,32.8635 73.3859,31.4295 73.158,30.0397 72.9309,28.6772         72.6954,27.3559 72.4506,26.0664 72.1964,24.803 71.9303,23.6004 71.6667,22.4176 71.3904,21.2829 71.1055,20.1399 70.8241,19.0711 70.5268,18.0073 70.2173,16.9881         70.1098,16.6168       </gml:coordinates>    </gml:LinearRing>  </gml:outerBoundaryIs></gml:Polygon>",
                },
                {"name": "format"},
                {
                    "name": "identifier",
                    "content": "S3A_SL_1_RBT____20240202T180852_20240202T181152_20240204T034253_0179_108_298_1080_PS1_O_NT_004",
                },
                {"name": "sensoroperationalmode", "content": "Earth Observation"},
                {
                    "name": "footprint",
                    "content": "POLYGON ((16.6168 70.1098, 21.4051 68.0469, 25.4819 65.839, 28.9145 63.5428, 31.8309 61.1872, 31.8562 61.1836, 32.173 61.2697, 33.0015 61.4834, 33.872 61.6886, 34.7351 61.8939, 35.6021 62.092, 36.4883 62.28, 37.3905 62.4753, 38.2995 62.6545, 39.2264 62.8295, 40.1581 62.9968, 41.0982 63.1585, 42.045 63.3231, 43.0157 63.4733, 43.9862 63.617, 44.9638 63.7541, 45.9522 63.8842, 46.9765 64.0082, 47.9718 64.1187, 48.9817 64.2322, 50.0184 64.3298, 51.0473 64.4319, 52.0811 64.5222, 53.1515 64.5952, 54.2045 64.6685, 55.2546 64.733, 56.3232 64.7927, 57.3918 64.845, 58.4526 64.8927, 59.531 64.9256, 60.6046 64.9481, 60.6036 64.9568, 60.3023 67.5657, 60.0271 70.182, 59.7903 72.7971, 59.6135 75.3677, 57.8034 75.3645, 56.019 75.3251, 54.208 75.2949, 52.4261 75.2383, 50.6494 75.1685, 48.9112 75.0884, 47.1653 74.9876, 45.4774 74.8821, 43.8062 74.7605, 42.1595 74.629, 40.5075 74.4821, 38.9256 74.3229, 37.338 74.162, 35.8086 73.9826, 34.3222 73.793, 32.8635 73.5943, 31.4295 73.3859, 30.0397 73.158, 28.6772 72.9309, 27.3559 72.6954, 26.0664 72.4506, 24.803 72.1964, 23.6004 71.9303, 22.4176 71.6667, 21.2829 71.3904, 20.1399 71.1055, 19.0711 70.8241, 18.0073 70.5268, 16.9881 70.2173, 16.6168 70.1098))",
                },
                {"name": "producttype", "content": "SL_1_RBT___"},
                {"name": "platformname", "content": "SENTINEL-3"},
                {"name": "size", "content": "378.62 MB"},
                {"name": "timeliness", "content": "NT"},
                {"name": "orbitdirection", "content": "ASCENDING"},
                {"name": "processinglevel", "content": "1"},
                {"name": "uuid", "content": "57897bfd-91a5-441f-a39b-a9159d9a410f"},
            ],
        },
    ]
    return response_json


@pytest.fixture(scope="module")
def raw_products(api_kwargs, vcr, test_wkt):
    """A fixture for tests that need some non-specific set of products in the form of a raw response as input."""
    with vcr.use_cassette("products_fixture", decode_compressed_response=False):
        api = SentinelAPI(**api_kwargs)
        raw_products = api._load_query(api.format_query(test_wkt, ("20151219", "20151228")))[0]
    return raw_products


def _get_smallest(api_kwargs, cassette, online, n=3):
    time_range = ("NOW-1MONTH", None) if online else (None, "20170101")
    odatas = []
    with cassette:
        api = SentinelAPI(**api_kwargs)
        products = api.query(date=time_range, size="/.+KB/", limit=15)
        for uuid in products:
            odata = api.get_product_odata(uuid)
            if odata["Online"] == online:
                odatas.append(odata)
                if len(odatas) == n:
                    break
    assert len(odatas) == n
    return odatas


@pytest.fixture(scope="module")
def smallest_online_products(api_kwargs, vcr):
    return _get_smallest(api_kwargs, vcr.use_cassette("smallest_online_products"), online=True)


@pytest.fixture(scope="module")
def smallest_archived_products(api_kwargs, vcr):
    return _get_smallest(api_kwargs, vcr.use_cassette("smallest_archived_products"), online=False)


@pytest.fixture(scope="module")
def quicklook_products(api_kwargs, vcr):
    ids = [
        "6b126ea4-fe27-440c-9a5c-686f386b7291",
        "1a9401bc-6986-4707-b38d-f6c29ca58c00",
        "54e6c4ad-6f4e-4fbf-b163-1719f60bfaeb",
    ]
    with vcr.use_cassette("quicklook_products"):
        api = SentinelAPI(**api_kwargs)
        odata = [api.get_product_odata(x) for x in ids]
    return odata


@pytest.fixture(scope="module")
def node_test_products(api_kwargs, vcr):
    with vcr.use_cassette("node_test_products"):
        api = SentinelAPI(**api_kwargs)
        products = api.query(date=("NOW-1MONTH", None), identifier="*IW_GRDH*", limit=3)
        odatas = [api.get_product_odata(x) for x in products]
        assert all(info["Online"] for info in odatas)
    return odatas


@pytest.fixture(scope="session")
def small_query():
    return dict(
        area="POLYGON((0 0,1 1,0 1,0 0))", date=(datetime(2015, 1, 1), datetime(2015, 1, 2))
    )


@pytest.fixture(scope="session")
def large_query():
    return dict(
        area="POLYGON((0 0,0 10,10 10,10 0,0 0))",
        date=(datetime(2015, 12, 1), datetime(2015, 12, 31)),
    )


@pytest.fixture(autouse=True)
def disable_waiting(monkeypatch):
    monkeypatch.setattr(sentinelsat.download, "_wait", lambda event, timeout: event.wait(0.001))
