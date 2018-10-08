import re
from os.path import join

from vcr.serializers import yamlserializer


class BinaryContentSerializer:
    """
    Serializer that stores any binary content in queries on disk as separate files
    """

    def __init__(self, directory='.', base_serializer=yamlserializer):
        self.directory = directory
        self.base_serializer = base_serializer

    def deserialize(self, cassette_string):
        cassette_dict = self.base_serializer.deserialize(cassette_string)
        for interaction in cassette_dict['interactions']:
            response = interaction['response']
            headers = response['headers']
            if 'Content-Range' in headers and 'Content-Disposition' in headers:
                rg, size, filename = self._parse_headers(headers)
                with open(join(self.directory, filename), 'rb') as f:
                    f.seek(rg[0])
                    content = f.read(rg[1] - rg[0] + 1)
                response['body']['string'] = content
        return cassette_dict

    def serialize(self, cassette_dict):
        for interaction in cassette_dict['interactions']:
            response = interaction['response']
            headers = response['headers']
            if 'Content-Range' in headers and 'Content-Disposition' in headers:
                rg, size, filename = self._parse_headers(headers)
                content = response['body']['string']
                if rg[0] == 0 and rg[1] + 1 == size:
                    with open(join(self.directory, filename), 'wb') as f:
                        f.write(content)
                del response['body']['string']
        return self.base_serializer.serialize(cassette_dict)

    @staticmethod
    def _parse_headers(headers):
        range_hdr = headers['Content-Range'][0]
        m = re.match(r"^bytes (\d+)-(\d+)/(\d+)", range_hdr)
        rg = (int(m.group(1)), int(m.group(2)))
        size = int(m.group(3))
        filename = headers['Content-Disposition'][0].split('"')[1]
        return rg, size, filename
