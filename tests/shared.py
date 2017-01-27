import warnings
from glob import glob
from os import environ, unlink

import pytest
import vcr

vcr_option = pytest.config.getoption("--vcr")
record_mode = "none"
if vcr_option == "use":
    print("Tests will use prerecorded query responses.")
elif vcr_option == "record_new":
    print("Tests will use prerecorded query responses and record any new ones.")
    record_mode = "new_episodes"
elif vcr_option == "reset_all":
    print("Tests will re-record all query responses. All existing cassettes will be erased.")
    record_mode = "all"
    for cassette_file in glob('tests/vcr_cassettes/*.yaml'):
        unlink(cassette_file)

def scrub_response(response):
    if "Set-Cookie" in response["headers"]:
        del response["headers"]["Set-Cookie"]
    return response

if vcr_option != "disable":
    my_vcr = vcr.VCR(
        record_mode=record_mode,
        serializer='yaml',
        cassette_library_dir='tests/vcr_cassettes/',
        path_transformer=vcr.VCR.ensure_suffix('.yaml'),
        match_on=['url', 'method', 'query'],
        filter_headers=['Set-Cookie'],
        before_record_response=scrub_response,
        decode_compressed_response=True
    )
else:
    print("Tests will not use any prerecorded query responses.")
    class DummyVCR:
        @staticmethod
        def use_cassette(func=None, *args, **kwargs):
            if not func:
                return lambda x: x
            return func
    my_vcr = DummyVCR()

if vcr_option != "use" and ('SENTINEL_USER' not in environ or 'SENTINEL_PASSWORD' not in environ):
    warnings.warn("Credentials are not set while not using prerecorded queries: "
                  "please set SENTINEL_USER and SENTINEL_PASSWORD environment variables.")
