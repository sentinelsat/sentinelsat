import logging
import os

import click
import geojson as gj

from sentinelsat import __version__ as sentinelsat_version
from sentinelsat.sentinel import SentinelAPI, SentinelAPIError, geojson_to_wkt, read_geojson

logger = logging.getLogger('sentinelsat')


def _set_logger_handler(level='INFO'):
    logger.setLevel(level)
    h = logging.StreamHandler()
    h.setLevel(level)
    fmt = logging.Formatter('%(message)s')
    h.setFormatter(fmt)
    logger.addHandler(h)


@click.group()
def cli():
    _set_logger_handler()


@cli.command()
@click.argument('user', type=str, metavar='<user>')
@click.argument('password', type=str, metavar='<password>')
@click.argument('geojson', type=click.Path(exists=True), metavar='<geojson>')
@click.option(
    '--start', '-s', type=str, default='NOW-1DAY',
    help='Start date of the query in the format YYYYMMDD.')
@click.option(
    '--end', '-e', type=str, default='NOW',
    help='End date of the query in the format YYYYMMDD.')
@click.option(
    '--download', '-d', is_flag=True,
    help='Download all results of the query.')
@click.option(
    '--footprints', '-f', is_flag=True,
    help="""Create a geojson file search_footprints.geojson with footprints
    and metadata of the returned products.
    """)
@click.option(
    '--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
@click.option(
    '--query', '-q', type=str, default=None,
    help="""Extra search keywords you want to use in the query. Separate
        keywords with comma. Example: 'producttype=GRD,polarisationmode=HH'.
        """)
@click.option(
    '--url', '-u', type=str, default='https://scihub.copernicus.eu/apihub/',
    help="""Define another API URL. Default URL is
        'https://scihub.copernicus.eu/apihub/'.
        """)
@click.option(
    '--md5', is_flag=True,
    help="""Verify the MD5 checksum and write corrupt product ids and filenames
    to corrupt_scenes.txt.
    """)
# DEPRECATED: to be removed with next major release
@click.option(
    '--sentinel1', is_flag=True,
    help='DEPRECATED: Please use --sentinel instead. Limit search to Sentinel-1 products.')
# DEPRECATED: to be removed with next major release
@click.option(
    '--sentinel2', is_flag=True,
    help='DEPRECATED: Please use --sentinel instead. Limit search to Sentinel-2 products.')
@click.option(
    '--sentinel', type=click.Choice(['1', '2', '3']),
    help='Limit search to a Sentinel satellite (constellation)')
@click.option(
    '--instrument', type=click.Choice(['MSI', 'SAR-C SAR', 'SLSTR', 'OLCI', 'SRAL']),
    help='Limit search to a specific instrument on a Sentinel satellite.')
@click.option(
    '--producttype', type=click.Choice(['SLC', 'GRD', 'OCN', 'RAW', 'S2MSI1C', 'S2MSI2Ap']),
    help='Limit search to a Sentinel product type.')
@click.option(
    '-c', '--cloud', type=int,
    help='Maximum cloud cover in percent. (requires --sentinel to be 2 or 3)')
@click.version_option(version=sentinelsat_version, prog_name="sentinelsat")
def search(
        user, password, geojson, start, end, download, md5, sentinel, producttype,
        instrument, sentinel1, sentinel2, cloud, footprints, path, query, url):
    """Search for Sentinel products and, optionally, download all the results
    and/or create a geojson file with the search result footprints.
    Beyond your SciHub user and password, you must pass a geojson file
    containing the polygon of the area you want to search for. If you
    don't specify the start and end dates, it will search in the last 24 hours.
    """

    api = SentinelAPI(user, password, url)

    search_kwargs = {}
    if sentinel and not (producttype or instrument):
        search_kwargs["platformname"] = "Sentinel-" + sentinel

    if instrument and not producttype:
        search_kwargs["instrumentshortname"] = instrument

    if producttype:
        search_kwargs["producttype"] = producttype

    if cloud:
        if sentinel not in ['2', '3']:
            logger.error('Cloud cover is only supported for Sentinel 2 and 3.')
            raise ValueError('Cloud cover is only supported for Sentinel 2 and 3.')
        search_kwargs["cloudcoverpercentage"] = "[0 TO %s]" % cloud

    # DEPRECATED: to be removed with next major release
    elif sentinel2:
        search_kwargs["platformname"] = "Sentinel-2"
        logger.info('DEPRECATED: Please use --sentinel instead')

    # DEPRECATED: to be removed with next major release
    elif sentinel1:
        search_kwargs["platformname"] = "Sentinel-1"
        logger.info('DEPRECATED: Please use --sentinel instead')

    if query is not None:
        search_kwargs.update((x.split('=') for x in query.split(',')))

    wkt = geojson_to_wkt(read_geojson(geojson))
    products = api.query(wkt, start, end, **search_kwargs)

    if footprints is True:
        footprints_geojson = api.to_geojson(products)
        with open(os.path.join(path, "search_footprints.geojson"), "w") as outfile:
            outfile.write(gj.dumps(footprints_geojson))

    if download is True:
        product_infos, failed_downloads = api.download_all(products, path, checksum=md5)
        if md5 is True:
            if len(failed_downloads) > 0:
                with open(os.path.join(path, "corrupt_scenes.txt"), "w") as outfile:
                    for failed_id in failed_downloads:
                        outfile.write("%s : %s\n" % (failed_id, products[failed_id]['title']))
    else:
        for product_id, props in products.items():
            logger.info('Product %s - %s' % (product_id, props['summary']))
        logger.info('---')
        logger.info(
            '%s scenes found with a total size of %.2f GB' %
            (len(products), api.get_products_size(products)))


@cli.command()
@click.argument('user', type=str, metavar='<user>')
@click.argument('password', type=str, metavar='<password>')
@click.argument('productid', type=str, metavar='<productid>')
@click.option(
    '--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
@click.option(
    '--url', '-u', type=str, default='https://scihub.copernicus.eu/apihub/',
    help="""Define another API URL. Default URL is
        'https://scihub.copernicus.eu/apihub/'.
        """)
@click.option(
    '--md5', is_flag=True,
    help="""Verify the MD5 checksum and write corrupt product ids and filenames
    to corrupt_scenes.txt.')
    """)
@click.version_option(version=sentinelsat_version, prog_name="sentinelsat")
def download(user, password, productid, path, md5, url):
    """Download a Sentinel Product. It just needs your SciHub user and password
    and the id of the product you want to download.
    """
    api = SentinelAPI(user, password, url)
    try:
        api.download(productid, path, md5)
    except SentinelAPIError as e:
        if 'Invalid key' in e.msg:
            logger.error('No product with ID \'%s\' exists on server', productid)
        else:
            raise
