__version__ = '0.11'

# Import for backwards-compatibility
from . import sentinel

from .sentinel import SentinelAPI, SentinelAPIError, InvalidChecksumError, read_geojson,\
    geojson_to_wkt, format_query_date
