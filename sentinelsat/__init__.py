__version__ = '0.13'

# Import for backwards-compatibility
from . import sentinel
from .exceptions import *
from .sentinel import SentinelAPI, format_query_date, geojson_to_wkt, read_geojson
