__version__ = "0.13"

# Import for backwards-compatibility
from . import sentinel

from .sentinel import (
    InvalidChecksumError,
    SentinelAPI,
    SentinelAPIError,
    SentinelAPILTAError,
    format_query_date,
    geojson_to_wkt,
    read_geojson,
)
