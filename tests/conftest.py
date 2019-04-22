from os import environ
from os.path import join, isfile, dirname, abspath

import pytest
import yaml
from pytest_socket import disable_socket
from vcr import VCR

from sentinelsat import SentinelAPI, geojson_to_wkt, read_geojson
from .custom_serializer import BinaryContentSerializer

TESTS_DIR = dirname(abspath(__file__))
FIXTURES_DIR = join(TESTS_DIR, 'fixtures')
CASSETTE_DIR = join(FIXTURES_DIR, 'vcr_cassettes')


# Configure pytest-vcr
@pytest.fixture(scope='module')
def vcr(vcr):
    def scrub_request(request):
        for header in ("Authorization", "Set-Cookie", "Cookie"):
            if header in request.headers:
                del request.headers[header]
        return request

    def scrub_response(response):
        for header in ("Authorization", "Set-Cookie", "Cookie", "Date", "Expires", "Transfer-Encoding"):
            if header in response["headers"]:
                del response["headers"][header]
        return response

    def range_header_matcher(r1, r2):
        return r1.headers.get('Range', '') == r2.headers.get('Range', '')

    vcr.cassette_library_dir = CASSETTE_DIR
    vcr.path_transformer = VCR.ensure_suffix('.yaml')
    vcr.filter_headers = ['Set-Cookie']
    vcr.before_record_request = scrub_request
    vcr.before_record_response = scrub_response
    vcr.decode_compressed_response = True
    vcr.register_serializer('custom', BinaryContentSerializer(CASSETTE_DIR))
    vcr.serializer = 'custom'
    vcr.register_matcher('range_header', range_header_matcher)
    vcr.match_on = ['uri', 'method', 'body', 'range_header']
    return vcr


@pytest.fixture(scope='session')
def credentials(request):
    # local tests require environment variables `DHUS_USER` and `DHUS_PASSWORD`
    # for Travis CI they are set as encrypted environment variables and stored
    record_mode = request.config.getoption('--vcr-record')
    disable_vcr = request.config.getoption('--disable-vcr')
    if record_mode in ["none", None] and not disable_vcr:
        # Using VCR.py cassettes for pre-recorded query playback
        # Any network traffic will raise an exception
        disable_socket()
    elif 'DHUS_USER' not in environ or 'DHUS_PASSWORD' not in environ:
        raise ValueError("Credentials must be set when --vcr-record is not none or --disable-vcr is used. "
                         "Please set DHUS_USER and DHUS_PASSWORD environment variables.")

    return [environ.get('DHUS_USER'), environ.get('DHUS_PASSWORD')]


@pytest.fixture(scope='session')
def api_kwargs(credentials):
    user, password = credentials
    return dict(user=user, password=password, api_url='https://scihub.copernicus.eu/apihub/')


@pytest.fixture
def api(api_kwargs):
    return SentinelAPI(**api_kwargs)


@pytest.fixture(scope='session')
def fixture_path():
    return lambda filename: join(FIXTURES_DIR, filename)


@pytest.fixture(scope='session')
def read_fixture_file(fixture_path):
    def read_func(filename, mode='r'):
        with open(fixture_path(filename), mode) as f:
            return f.read()

    return read_func


@pytest.fixture(scope='session')
def read_yaml(read_fixture_file):
    return lambda filename: yaml.safe_load(read_fixture_file(filename))


@pytest.fixture(scope='session')
def geojson_path():
    path = join(FIXTURES_DIR, 'map.geojson')
    assert isfile(path)
    return path


@pytest.fixture(scope='session')
def test_wkt(geojson_path):
    return geojson_to_wkt(read_geojson(geojson_path))
