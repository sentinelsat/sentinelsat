import types
import warnings
from os import environ
from os.path import abspath, dirname, join

import pytest
import vcr
from pytest_socket import disable_socket

from .custom_serializer import BinaryContentSerializer

TESTS_DIR = dirname(abspath(__file__))
FIXTURES_DIR = join(TESTS_DIR, 'fixtures')
CASSETTE_DIR = join(FIXTURES_DIR, 'vcr_cassettes')
PROJECT_ROOT_DIR = dirname(TESTS_DIR)

vcr_option = pytest.config.getoption("--vcr")
record_mode = "none"
if vcr_option == "use":
    print("Tests will use prerecorded query responses.")
    # Guarantee that only prerecorded queries are used by blocking any network traffic
    disable_socket()
elif vcr_option == "record_new":
    print("Tests will use prerecorded query responses and record any new ones.")
    record_mode = "new_episodes"
elif vcr_option == "reset":
    print("Tests will re-record query responses.")
    record_mode = "all"


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


if vcr_option != "disable":
    my_vcr = vcr.VCR(
        record_mode=record_mode,
        cassette_library_dir=CASSETTE_DIR,
        path_transformer=vcr.VCR.ensure_suffix('.yaml'),
        filter_headers=['Set-Cookie'],
        before_record_request=scrub_request,
        before_record_response=scrub_response,
        decode_compressed_response=True
    )
    my_vcr.register_serializer('custom', BinaryContentSerializer(CASSETTE_DIR))
    my_vcr.serializer = 'custom'
    my_vcr.register_matcher('range_header', range_header_matcher)
    my_vcr.match_on = ['uri', 'method', 'body', 'range_header']
else:
    print("Tests will not use any prerecorded query responses.")

    class DummyCassette:
        def __enter__(self):
            return

        def __exit__(self, *args):
            return

        def __call__(self, func, *args, **kwargs):
            return func

    class DummyVCR:
        @staticmethod
        def use_cassette(func=None, *args, **kwargs):
            if not isinstance(func, types.FunctionType):
                return DummyCassette()
            return func

    my_vcr = DummyVCR()

if vcr_option != "use" and ('DHUS_USER' not in environ or 'DHUS_PASSWORD' not in environ):
    warnings.warn("Credentials are not set while not using prerecorded queries: "
                  "please set DHUS_USER and DHUS_PASSWORD environment variables.")
