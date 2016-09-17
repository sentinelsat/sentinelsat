import click
import geojson as gj

import os

from sentinelsat.sentinel import SentinelAPI, get_coordinates


@click.group()
def cli():
    pass


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
    help="""Create a geojson file search_footprints.geojson with footprints of
    the query result.
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
@click.option(
    '--sentinel1', is_flag=True,
    help='Limit search to Sentinel-1 products.')
@click.option(
    '--sentinel2', is_flag=True,
    help='Limit search to Sentinel-2 products.')
@click.option(
    '-c', '--cloud', type=int,
    help='Maximum cloud cover in percent. (Automatically sets --sentinel2)')
def search(
        user, password, geojson, start, end, download, md5,
        sentinel1, sentinel2, cloud, footprints, path, query, url):
    """Search for Sentinel products and, optionally, download all the results
    and/or create a geojson file with the search result footprints.
    Beyond your SciHub user and password, you must pass a geojson file
    containing the polygon of the area you want to search for. If you
    don't specify the start and end dates, it will search in the last 24 hours.
    """
    api = SentinelAPI(user, password, url)

    search_kwargs = {}
    if cloud:
        search_kwargs.update(
            {"platformname": "Sentinel-2",
            "cloudcoverpercentage": "[0 TO %s]" % cloud})
    elif sentinel2:
        search_kwargs.update({"platformname": "Sentinel-2"})
    elif sentinel1:
        search_kwargs.update({"platformname": "Sentinel-1"})

    if query is not None:
        search_kwargs.update(dict([i.split('=') for i in query.split(',')]))

    api.query(get_coordinates(geojson), start, end, **search_kwargs)

    if footprints is True:
        footprints_geojson = api.get_footprints()
        with open(os.path.join(path, "search_footprints.geojson"), "w") as outfile:
            outfile.write(gj.dumps(footprints_geojson))

    if download is True:
        result = api.download_all(path, checksum=md5)
        if md5 is True:
            corrupt_scenes = [(path, info["id"]) for path, info in result.items() if info is not None]
            if len(corrupt_scenes) > 0:
                with open(os.path.join(path, "corrupt_scenes.txt"), "w") as outfile:
                    for corrupt_tuple in corrupt_scenes:
                        outfile.write("%s : %s\n" % corrupt_tuple)
    else:
        for product in api.get_products():
            print('Product %s - %s' % (product['id'], product['summary']))
        print('---')
        print(
            '%s scenes found with a total size of %.2f GB' %
            (len(api.get_products()), api.get_products_size()))


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
def download(user, password, productid, path, md5, url):
    """Download a Sentinel Product. It just needs your SciHub user and password
    and the id of the product you want to download.
    """
    api = SentinelAPI(user, password, url)
    api.download(productid, path, md5)
