import click

import os
import geojson as gj
from sentinelsat.sentinel import SentinelAPI, get_coordinates


@click.group()
def cli():
    pass


@cli.command()
@click.argument('user', type=str, metavar='<user>')
@click.argument('password', type=str, metavar='<password>')
@click.argument('geojson', type=click.Path(exists=True), metavar='<geojson>')
@click.option('--start', '-s', type=str, default='NOW-1DAY',
    help='Start date of the query in the format YYYYMMDD.')
@click.option('--end', '-e', type=str, default='NOW',
    help='End date of the query in the format YYYYMMDD.')
@click.option('--download', '-d', is_flag=True,
    help='Download all results of the query.')
@click.option('--footprints', '-f', is_flag=True,
    help='Create geojson file with footprints of the query result.')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
@click.option('--query', '-q', type=str, default=None,
    help="""Extra search keywords you want to use in the query. Separate
        keywords with comma. Example: 'producttype=GRD,polarisationmode=HH'.
        """)
def search(user, password, geojson, start, end, download, footprints, path, query):
    """Search for Sentinel-1 products and, optionally, download all the results
    and/or create a geojson file with the search result footprints.
    Beyond your SciHub user and password, you must pass a geojson file
    containing the polygon of the area you want to search for. If you
    don't specify the start and end dates, it will search in the last 24 hours.
    """
    api = SentinelAPI(user, password)
    if query is not None:
        query = dict([i.split('=') for i in query.split(',')])
        api.query(get_coordinates(geojson), start, end, **query)
    else:
        api.query(get_coordinates(geojson), start, end)

    if footprints is True:
        footprints_geojson = api.get_footprints()
        with open(os.path.join(path, "search_footprints.geojson"), "w") as outfile:
            outfile.write(gj.dumps(footprints_geojson))

    if download is True:
        api.download_all(path)
    else:
        for product in api.get_products():
            print('Product %s - %s' % (product['id'], product['summary']))


@cli.command()
@click.argument('user', type=str, metavar='<user>')
@click.argument('password', type=str, metavar='<password>')
@click.argument('productid', type=str, metavar='<productid>')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
def download(user, password, productid, path):
    """Download a Sentinel-1 Product. It just needs your SciHub user and password
    and the id of the product you want to download.
    """
    api = SentinelAPI(user, password)
    api.download(productid, path)
