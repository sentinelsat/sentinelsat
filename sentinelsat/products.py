# SentinelProductsAPI functionality has been merged into SentinelAPI and Downloader
# This file is for backwards compatibility only and will be removed in a future release.
import warnings
from sentinelsat.sentinel import SentinelAPI
from sentinelsat.download import (
    make_path_filter,
    make_size_filter,
    all_nodes_filter,
)

SentinelProductsAPI = SentinelAPI

warnings.warn(
    "sentinelsat.products has been deprecated and will be removed in a future release",
    DeprecationWarning,
    stacklevel=2,
)
