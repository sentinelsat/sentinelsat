__version__ = "1.1.1"

# Import for backwards-compatibility
from . import sentinel
from .exceptions import (
    SentinelAPIError,
    LTAError,
    LTATriggered,
    ServerError,
    InvalidKeyError,
    QueryLengthError,
    QuerySyntaxError,
    UnauthorizedError,
    InvalidChecksumError,
)
from .sentinel import (
    SentinelAPI,
    format_query_date,
    geojson_to_wkt,
    read_geojson,
    placename_to_wkt,
)
from .download import (
    Downloader,
    DownloadStatus,
)
from .products import all_nodes_filter, make_path_filter, make_size_filter, SentinelProductsAPI
