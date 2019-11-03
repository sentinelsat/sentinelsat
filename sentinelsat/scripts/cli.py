import logging
import os

import click
import geojson as gj
import requests.utils

from sentinelsat import __version__ as sentinelsat_version
from sentinelsat.sentinel import SentinelAPI, SentinelAPIError, geojson_to_wkt, read_geojson

logger = logging.getLogger("sentinelsat")


def _set_logger_handler(level="INFO"):
    logger.setLevel(level)
    h = logging.StreamHandler()
    h.setLevel(level)
    fmt = logging.Formatter("%(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)


class CommaSeparatedString(click.ParamType):
    name = "comma-string"

    def convert(self, value, param, ctx):
        if value:
            return value.split(",")
        else:
            return value


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
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
    default="https://scihub.copernicus.eu/apihub/",
    envvar="DHUS_URL",
    help="""Define API URL. Default URL is
        'https://scihub.copernicus.eu/apihub/' (or environment variable DHUS_URL).
        """,
)
@click.option(
    "--start",
    "-s",
    default="NOW-1DAY",
    show_default=True,
    help="Start date of the query in the format YYYYMMDD.",
)
@click.option(
    "--end",
    "-e",
    default="NOW",
    show_default=True,
    help="End date of the query in the format YYYYMMDD.",
)
@click.option(
    "--geometry", "-g", type=click.Path(exists=True), help="Search area geometry as GeoJSON file."
)
@click.option(
    "--uuid",
    type=CommaSeparatedString(),
    default=None,
    help="Select a specific product UUID instead of a query. Multiple UUIDs can separated by comma.",
)
@click.option(
    "--name",
    type=CommaSeparatedString(),
    default=None,
    help="Select specific product(s) by filename. Supports wildcards.",
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
@click.option(
    "--path",
    type=click.Path(exists=True),
    default=".",
    help="Set the path where the files will be saved.",
)
@click.option(
    "--query",
    "-q",
    type=CommaSeparatedString(),
    default=None,
    help="""Extra search keywords you want to use in the query. Separate
        keywords with comma. Example: 'producttype=GRD,polarisationmode=HH'.
        """,
)
@click.option(
    "--footprints",
    is_flag=True,
    help="""Create a geojson file search_footprints.geojson with footprints
    and metadata of the returned products.
    """,
)
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
    sentinel,
    producttype,
    instrument,
    cloud,
    footprints,
    path,
    query,
    url,
    order_by,
    limit,
):
    """Search for Sentinel products and, optionally, download all the results
    and/or create a geojson file with the search result footprints.
    Beyond your Copernicus Open Access Hub user and password, you must pass a geojson file
    containing the geometry of the area you want to search for or the UUIDs of the products. If you
    don't specify the start and end dates, it will search in the last 24 hours.
    """

    _set_logger_handler()

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

    api = SentinelAPI(user, password, url)

    search_kwargs = {}
    if sentinel and not (producttype or instrument):
        search_kwargs["platformname"] = "Sentinel-" + sentinel

    if instrument and not producttype:
        search_kwargs["instrumentshortname"] = instrument

    if producttype:
        search_kwargs["producttype"] = producttype

    if cloud:
        if sentinel not in ["2", "3"]:
            logger.error("Cloud cover is only supported for Sentinel 2 and 3.")
            exit(1)
        search_kwargs["cloudcoverpercentage"] = (0, cloud)

    if query is not None:
        search_kwargs.update((x.split("=") for x in query))

    if geometry is not None:
        search_kwargs["area"] = geojson_to_wkt(read_geojson(geometry))

    if uuid is not None:
        uuid_list = [x.strip() for x in uuid]
        products = {}
        for productid in uuid_list:
            try:
                products[productid] = api.get_product_odata(productid)
            except SentinelAPIError as e:
                if "Invalid key" in e.msg:
                    logger.error("No product with ID '%s' exists on server", productid)
                    exit(1)
                else:
                    raise
    elif name is not None:
        search_kwargs["identifier"] = name[0] if len(name) == 1 else "(" + " OR ".join(name) + ")"
        products = api.query(order_by=order_by, limit=limit, **search_kwargs)
    else:
        start = start or "19000101"
        end = end or "NOW"
        products = api.query(date=(start, end), order_by=order_by, limit=limit, **search_kwargs)

    if footprints is True:
        footprints_geojson = api.to_geojson(products)
        with open(os.path.join(path, "search_footprints.geojson"), "w") as outfile:
            outfile.write(gj.dumps(footprints_geojson))

    if download is True:
        product_infos, triggered, failed_downloads = api.download_all(products, path)
        if len(failed_downloads) > 0:
            with open(os.path.join(path, "corrupt_scenes.txt"), "w") as outfile:
                for failed_id in failed_downloads:
                    outfile.write("%s : %s\n" % (failed_id, products[failed_id]["title"]))
    else:
        for product_id, props in products.items():
            if uuid is None:
                logger.info("Product %s - %s", product_id, props["summary"])
            else:  # querying uuids has no summary key
                logger.info(
                    "Product %s - %s - %s MB",
                    product_id,
                    props["title"],
                    round(int(props["size"]) / (1024.0 * 1024.0), 2),
                )
        if uuid is None:
            logger.info("---")
            logger.info(
                "%s scenes found with a total size of %.2f GB",
                len(products),
                api.get_products_size(products),
            )
