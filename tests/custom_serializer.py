"""
Custom serializer that stores any binary product data in queries on disk as files
"""
import re
from os.path import abspath, dirname, join

import yaml

# Use the libYAML versions if possible
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

tests_dir = dirname(abspath(__file__))
cassettes_dir = tests_dir + '/fixtures/vcr_cassettes/'


def _parse_headers(response):
    range_hdr = response['headers']['Content-Range'][0]
    m = re.match(r"^bytes (\d+)-(\d+)/(\d+)", range_hdr)
    rg = (int(m.group(1)), int(m.group(2)))
    size = int(m.group(3))
    filename = response['headers']['Content-Disposition'][0].split('"')[1]
    return rg, size, filename


def deserialize(cassette_string):
    cassette_dict = yaml.load(cassette_string, Loader=Loader)
    for interaction in cassette_dict['interactions']:
        request = interaction['request']
        response = interaction['response']
        uri = request.get('uri', '')
        if '/$value' not in uri:
            continue
        rg, size, filename = _parse_headers(response)
        with open(join(cassettes_dir, filename), 'rb') as f:
            content = f.read()
        response['body']['string'] = content[rg[0]:rg[1] + 1]
    return cassette_dict


def serialize(cassette_dict):
    for interaction in cassette_dict['interactions']:
        request = interaction['request']
        response = interaction['response']
        uri = request.get('uri', '')
        if '/$value' not in uri:
            continue
        rg, size, filename = _parse_headers(response)
        content = response['body']['string']
        if rg[0] == 0 and rg[1] + 1 == size:
            with open(join(cassettes_dir, filename), 'wb') as f:
                f.write(content)
        del response['body']['string']
    return yaml.dump(cassette_dict, Dumper=Dumper)
