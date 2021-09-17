import fnmatch
import warnings

from sentinelsat.sentinel import SentinelAPI


class SentinelProductsAPI(SentinelAPI):
    """
    .. deprecated:: 1.1.0
        SentinelProductsAPI functionality has been merged into SentinelAPI and Downloader
        and will be removed in a future release.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SentinelProductsAPI has been deprecated and will be removed in a future release",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


def make_size_filter(max_size):
    """Generate a nodefilter function to download only files below the specified maximum size.

    .. versionadded:: 0.15
    """

    def node_filter(node_info):
        return node_info["size"] <= max_size

    return node_filter


def make_path_filter(pattern, exclude=False):
    """Generate a nodefilter function to download only files matching the specified pattern.

    Parameters
    ----------
    pattern : str
        glob patter for files selection
    exclude : bool, optional
        if set to True then files matching the specified pattern are excluded. Default False.

    .. versionadded:: 0.15
    """

    def node_filter(node_info):
        match = fnmatch.fnmatch(node_info["node_path"], pattern)
        return not match if exclude else match

    return node_filter


def all_nodes_filter(node_info):
    """Node filter function to download all files.

    This function can be used to download a Sentinel product as a directory
    instead of downloading a single zip archive.

    .. versionadded:: 0.15
    """
    return True
