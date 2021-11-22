import json
import logging
import math
import os
import re

import click
import geojson as gj
import requests.utils
from tqdm.auto import tqdm

from sentinelsat import __version__ as sentinelsat_version, make_path_filter
from sentinelsat.sentinel import SentinelAPI, geojson_to_wkt, is_wkt, placename_to_wkt, read_geojson

json_parse_exception = json.decoder.JSONDecodeError

logger = logging.getLogger("sentinelsat")


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


def _set_logger_handler(level="INFO"):
    logger.setLevel(level)
    if os.environ.get("DISABLE_TQDM_LOGGING"):
        # Intended for testing
        h = logging.StreamHandler()
    else:
        h = TqdmLoggingHandler()
    h.setLevel(level)
    h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(h)


def validate_query_param(ctx, param, kwargs):
    for kwarg in kwargs:
        if not re.match(r"\w+=.+", kwarg):
            raise click.BadParameter("must have the format 'keyword=value'")
    return kwargs


@click.command(context_settings=dict(help_option_names=["-h", "--help"]), no_args_is_help=True)
@click.option(
    "--user",
    "-u",
    envvar="DHUS_USER",
    default=None,
    help="Username (or environment variable DHUS_USER is set)",
)
@click.option(
    "--password",
    "-p",
    envvar="DHUS_PASSWORD",
    default=None,
    help="Password (or environment variable DHUS_PASSWORD is set)",
)
@click.option(
    "--url",
    default="https://apihub.copernicus.eu/apihub/",
    envvar="DHUS_URL",
    help="""Define API URL. Default URL is
        'https://apihub.copernicus.eu/apihub/' (or environment variable DHUS_URL).
        """,
)
@click.option(
    "--start",
    "-s",
    default=None,
    help="Start date of the query in the format YYYYMMDD or an expression like NOW-1DAY.",
)
@click.option(
    "--end",
    "-e",
    default=None,
    help="End date of the query.",
)
@click.option(
    "--geometry",
    "-g",
    type=str,
    help="Search area geometry as GeoJSON file, a GeoJSON string, or a WKT string. ",
)
@click.option(
    "--uuid",
    multiple=True,
    help="Select a specific product UUID. Can be set more than once.",
)
@click.option(
    "--name",
    multiple=True,
    help="Select specific product(s) by filename. Supports wildcards. Can be set more than once.",
)
@click.option(
    "--sentinel",
    type=click.Choice(["1", "2", "3", "5"]),
    help="Limit search to a Sentinel satellite (constellation)",
)
@click.option(
    "--instrument",
    type=click.Choice(["MSI", "SAR-C SAR", "SLSTR", "OLCI", "SRAL"]),
    help="Limit search to a specific instrument on a Sentinel satellite.",
)
@click.option(
    "--producttype", type=str, default=None, help="Limit search to a Sentinel product type."
)
@click.option(
    "-c",
    "--cloud",
    type=int,
    help="Maximum cloud cover in percent. (requires --sentinel to be 2 or 3)",
)
@click.option(
    "-o",
    "--order-by",
    help="Comma-separated list of keywords to order the result by. "
    "Prefix keywords with '-' for descending order.",
)
@click.option(
    "-l", "--limit", type=int, help="Maximum number of results to return. Defaults to no limit."
)
@click.option("--download", "-d", is_flag=True, help="Download all results of the query.")
@click.option("--fail-fast", is_flag=True, help="Skip all other other downloads if one fails")
@click.option(
    "--quicklook",
    is_flag=True,
    help="""Download quicklook of a product.""",
)
@click.option(
    "--path",
    type=click.Path(exists=True),
    default=".",
    help="Set the path where the files will be saved.",
)
@click.option(
    "--query",
    "-q",
    multiple=True,
    callback=validate_query_param,
    help="""Extra search keywords you want to use in the query. 
        Example: '-q producttype=GRD -q polarisationmode=HH'.
        Repeated keywords are interpreted as an "or" expression.
        """,
)
@click.option(
    "--location",
    type=str,
    help="Return only products overlapping with the bounding box of given location, "
    "e.g. 'Berlin', 'Germany' or '52.393974, 13.066955'.",
)
@click.option(
    "--footprints",
    type=click.File(mode="w", encoding="utf8", lazy=True),
    help="""Create a GeoJSON file at the provided path with footprints
    and metadata of the returned products. Set to '-' for stdout.
    """,
)
@click.option(
    "--timeout",
    type=float,
    default=60,
    help="How long to wait for a DataHub response (in seconds, default 60 sec).",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Print debug log messages.",
)
@click.option(
    "--include-pattern",
    default=None,
    help="""Glob pattern to filter files (within each product) to be downloaded.
    """,
)
@click.option(
    "--exclude-pattern",
    default=None,
    help="""Glob pattern to filter files (within each product) to be excluded
    from the downloaded.
    """,
)
@click.option(
    "--gnss",
    is_flag=True,
    help="""Use the "https://scihub.copernicus.eu/gnss" end-point
    for orbit data query and download.
    """,
)
@click.option(
    "--fmt",
    default="Product {uuid} - {summary}",
    show_default=True,
    help="""Specify a custom format to print results. The format string shall
    be compatible with the Python "Format Specification Mini-Language".

    Some common keywords for substitution are:
    'uuid', 'identifier', 'summary', 'link', 'size', 'platformname', 'producttype',
    'beginposition', 'instrumentshortname', 'cloudcoverpercentage',
    'orbitdirection', 'relativeorbitnumber', 'footprint'.

    For a complete set of available keywords see the "properties" output from a
    relevant query with ``--footprints -`` appended.
    """,
)
@click.option("--info", is_flag=True, is_eager=True, help="Displays the DHuS version used")
@click.version_option(version=sentinelsat_version, prog_name="sentinelsat")
def cli(
    user,
    password,
    geometry,
    start,
    end,
    uuid,
    name,
    download,
    fail_fast,
    quicklook,
    sentinel,
    producttype,
    instrument,
    cloud,
    footprints,
    path,
    query,
    url,
    order_by,
    location,
    limit,
    timeout,
    debug,
    include_pattern,
    exclude_pattern,
    gnss,
    fmt,
    info,
):
    """Search for Sentinel products and, optionally, download all the results
    and/or create a GeoJSON file with the search result footprints.
    Beyond your Copernicus Open Access Hub user and password, you will typically want to pass a GeoJSON file
    containing the geometry of the area you want to search for and the relevant time range.
    """

    if footprints and footprints.name == "-":
        _set_logger_handler("WARNING")
    elif debug:
        _set_logger_handler("DEBUG")
    else:
        _set_logger_handler("INFO")

    if info:
        api = SentinelAPI(None, None, url, timeout=timeout)
        ctx = click.get_current_context()
        click.echo("DHuS version: " + api.dhus_version)
        ctx.exit()

    if include_pattern is not None and exclude_pattern is not None:
        raise click.UsageError(
            "--include-pattern and --exclude-pattern cannot be specified together."
        )
    elif include_pattern is not None:
        nodefilter = make_path_filter(include_pattern)
    elif exclude_pattern is not None:
        nodefilter = make_path_filter(exclude_pattern, exclude=True)
    else:
        nodefilter = None

    if gnss:
        url = "https://scihub.copernicus.eu/gnss/"
        user = "gnssguest"
        password = "gnssguest"

    if user is None or password is None:
        try:
            user, password = requests.utils.get_netrc_auth(url)
        except TypeError:
            pass

    if user is None or password is None:
        raise click.UsageError(
            "Missing --user and --password. Please see docs "
            "for environment variables and .netrc support."
        )

    api = SentinelAPI(user, password, url, timeout=timeout)

    search_kwargs = {}
    if sentinel:
        search_kwargs["platformname"] = "Sentinel-" + sentinel

    if instrument:
        search_kwargs["instrumentshortname"] = instrument

    if producttype:
        search_kwargs["producttype"] = producttype

    if cloud:
        if sentinel not in ["2", "3"]:
            logger.error("Cloud cover is only supported for Sentinel 2 and 3.")
            exit(1)
        search_kwargs["cloudcoverpercentage"] = (0, cloud)

    if len(name) > 0:
        search_kwargs["identifier"] = set(name)

    if len(uuid) > 0:
        search_kwargs["uuid"] = set(uuid)

    if len(query) > 0:
        for kwarg in query:
            key, value = kwarg.split("=", 1)
            if key in search_kwargs:
                if isinstance(search_kwargs[key], set):
                    search_kwargs[key].add(value)
                else:
                    search_kwargs[key] = {search_kwargs[key], value}
            else:
                search_kwargs[key] = value

    if location is not None:
        wkt, info = placename_to_wkt(location)
        minX, minY, maxX, maxY = info["bbox"]
        r = 6371  # average radius, km
        extent_east = r * math.radians(maxX - minX) * math.cos(math.radians((minY + maxY) / 2))
        extent_north = r * math.radians(maxY - minY)
        logger.info(
            "Querying location: '%s' with %.1f x %.1f km, %f, %f to %f, %f bounding box",
            info["display_name"],
            extent_north,
            extent_east,
            minY,
            minX,
            maxY,
            maxX,
        )
        search_kwargs["area"] = wkt

    if geometry is not None:
        # check if the value is an existing path
        if os.path.exists(geometry):
            search_kwargs["area"] = geojson_to_wkt(read_geojson(geometry))
        # check if the value is a GeoJSON
        else:
            if geometry.startswith("{"):
                try:
                    geometry = json.loads(geometry)
                    search_kwargs["area"] = geojson_to_wkt(geometry)
                except json_parse_exception:
                    raise click.UsageError(
                        "geometry string starts with '{' but is not a valid GeoJSON."
                    )
            # check if the value is a WKT
            elif is_wkt(geometry):
                search_kwargs["area"] = geometry
            else:
                raise click.UsageError(
                    "The geometry input is neither a GeoJSON file with a valid path, "
                    "a GeoJSON String nor a WKT string."
                )

    products = api.query(date=(start, end), order_by=order_by, limit=limit, **search_kwargs)

    if footprints is not None:
        footprints_geojson = api.to_geojson(products)
        gj.dump(footprints_geojson, footprints)
        footprints.close()

    if quicklook:
        downloaded_quicklooks, failed_quicklooks = api.download_all_quicklooks(products, path)
        if failed_quicklooks:
            api.logger.warning(
                "Some quicklooks failed: %s out of %s", len(failed_quicklooks), len(products)
            )

    if download:
        downloaded, triggered, failed_downloads = api.download_all(
            products, path, nodefilter=nodefilter, fail_fast=fail_fast
        )
        retcode = 0
        if len(failed_downloads) > 0:
            retcode = 1
            with open(os.path.join(path, "corrupt_scenes.txt"), "w") as outfile:
                for failed_id in failed_downloads:
                    outfile.write("{} : {}\n".format(failed_id, products[failed_id]["title"]))
        logger.info(
            "Successfully downloaded %d/%d products.",
            len(downloaded),
            len(products),
        )
        exit(retcode)
    else:
        for product_id, props in products.items():
            logger.info(fmt.format(**props))
        logger.info("---")
        logger.info(
            "%s scenes found with a total size of %.2f GB",
            len(products),
            api.get_products_size(products),
        )
