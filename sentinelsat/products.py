import fnmatch
import warnings
import operator
import functools

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
    pattern : str, sequence[str]
        glob pattern (or sequence of patterns) for files selection
    exclude : bool, optional
        if set to True then files matching the specified pattern are excluded. Default False.
       The `pattern` parameter can also be a list of patterns.
    """

    patterns = [pattern] if isinstance(pattern, str) else pattern

    def node_filter(node_info):
        match = False
        for pattern in patterns:
            match = fnmatch.fnmatch(node_info["node_path"], pattern)
            if match:
                break

        return not match if exclude else match

    return node_filter


def all_nodes_filter(node_info):
    """Node filter function to download all files.

    This function can be used to download a Sentinel product as a directory
    instead of downloading a single zip archive.

    """
    return True


def chain_filters(filters, op=operator.or_, exclude=False):
    """Generate a nodefilter function by chaining a sequence of node filters.

    Parameters
    ----------
    filters : sequence
        sequence of node filter to be evaluated according to the operator `op`
    op : operator
        operator used to chain the input node filters (default `or`)
    exclude : bool, optional
        if set to True then files matching the specified pattern are excluded. Default False.

    """

    def node_filter(node_info):
        results = [nodefilter(node_info) for nodefilter in filters]
        result = functools.reduce(op, results)
        return not result if exclude else result

    return node_filter
