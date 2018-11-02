import os

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def pytest_addoption(parser):
    parser.addoption("--vcr", choices=("use", "disable", "record_new", "reset"), default="use",
                     help="Set how prerecorded queries are used:\n"
                          "use - replay cassettes but do not record (default),\n"
                          "disable - pass all queries directly to the server\n"
                          "record_new - replay cassettes and record any unmatched queries,\n"
                          "reset - re-record all matching cassettes.")


@pytest.fixture
def geojson_path():
    path = os.path.join(FIXTURES_DIR, 'map.geojson')
    assert os.path.isfile(path)
    return path
