import re
from os.path import join

from vcr.serializers import yamlserializer


class BinaryContentSerializer:
    """
    Serializer that stores any binary content in queries on disk as separate files
    """

    def __init__(self, directory=".", base_serializer=yamlserializer):
        self.directory = directory
        self.base_serializer = base_serializer

    def deserialize(self, cassette_string):
        cassette_dict = self.base_serializer.deserialize(cassette_string)
        for interaction in cassette_dict["interactions"]:
            if interaction["request"]["method"] == "HEAD":
                continue
            response = interaction["response"]
            headers = {k.lower(): v for k, v in response["headers"].items()}
            if "content-range" in headers and "content-disposition" in headers:
                rg, size, filename = self._parse_headers(headers)
                with open(join(self.directory, "data", filename), "rb") as f:
                    f.seek(rg[0])
                    content = f.read(rg[1] - rg[0] + 1)
                response["body"]["string"] = content
        return cassette_dict

    def serialize(self, cassette_dict):
        for interaction in cassette_dict["interactions"]:
            if interaction["request"]["method"] == "HEAD":
                continue
            response = interaction["response"]
            headers = {k.lower(): v for k, v in response["headers"].items()}
            if "content-range" in headers and "content-disposition" in headers:
                rg, size, filename = self._parse_headers(headers)
                content = response["body"]["string"]
                if hasattr(content, "encode"):
                    content = content.encode("utf-8")
                if rg[0] == 0 and rg[1] + 1 == size:
                    with open(join(self.directory, "data", filename), "wb") as f:
                        f.write(content)
                del response["body"]["string"]
        return self.base_serializer.serialize(cassette_dict)

    @staticmethod
    def _parse_headers(headers):
        range_hdr = headers["content-range"][0]
        m = re.match(r"^bytes (\d+)-(\d+)/(\d+)", range_hdr)
        rg = (int(m.group(1)), int(m.group(2)))
        size = int(m.group(3))
        filename = headers["content-disposition"][0].split('"')[1]
        return rg, size, filename
