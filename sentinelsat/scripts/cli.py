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
@click.option('--start', '-s', type=str, default='NOW-1DAY',
    help='Start date of the query in the format YYYYMMDD.')
@click.option('--end', '-e', type=str, default='NOW',
    help='End date of the query in the format YYYYMMDD.')
@click.option('--download', '-d', is_flag=True,
    help='Download all results of the query.')
@click.option('--check', '-c', is_flag=True,
    help='Verify the MD5 checksum and write corrupt product ids to a textfile.')
@click.option('--footprints', '-f', is_flag=True,
    help='Create a geojson file with footprints of the query result.')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
@click.option('--query', '-q', type=str, default=None,
    help="""Extra search keywords you want to use in the query. Separate
        keywords with comma. Example: 'producttype=GRD,polarisationmode=HH'.
        """)
@click.option('--url', '-u', type=str, default='https://scihub.esa.int/apihub/',
    help="""Define another API URL. Default URL is
        'https://scihub.esa.int/apihub/'.
        """)
def search(user, password, geojson, start, end, download, check, footprints, path, query, url):
    """Search for Sentinel-1 products and, optionally, download all the results
    and/or create a geojson file with the search result footprints.
    Beyond your SciHub user and password, you must pass a geojson file
    containing the polygon of the area you want to search for. If you
    don't specify the start and end dates, it will search in the last 24 hours.
    """
    api = SentinelAPI(user, password, url)
    if query is not None:
        query = dict([i.split('=') for i in query.split(',')])
        api.query(get_coordinates(geojson), start, end, **query)
    else:
        api.query(get_coordinates(geojson), start, end)

    if footprints is True:
        footprints_geojson = api.get_footprints()
        with open(os.path.join(path, "search_footprints.geojson"), "w") as outfile:
            outfile.write(gj.dumps(footprints_geojson))

    if download is True and check is True:
        corrupt_scenes = api.download_all(path, check)
        if len(corrupt_scenes) is not 0:
            with open(os.path.join(path, "corrupt_scenes.txt"), "w") as outfile:
                for product_id in corrupt_scenes:
                    outfile.write("%s\n" % product_id)
    elif download is True and check is False:
        api.download_all(path)
    else:
        size_total = 0
        for product in api.get_products():
            print('Product %s - %s' % (product['id'], product['summary']))
            size_product = float(next(x for x in product["str"] if x["name"] == "size")["content"][:-3])
            size_total += size_product
        print('---')
        print('%s scenes found with a total size of %s MB' % (len(api.get_products()), size_total))


@cli.command()
@click.argument('user', type=str, metavar='<user>')
@click.argument('password', type=str, metavar='<password>')
@click.argument('productid', type=str, metavar='<productid>')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
@click.option('--check', '-c', is_flag=True,
    help='Verify the MD5 checksum and write corrupt product ids to a textfile.')
@click.option('--url', '-u', type=str, default='https://scihub.esa.int/apihub/',
    help="""Define another API URL. Default URL is
        'https://scihub.esa.int/apihub/'.
        """)
def download(user, password, productid, path, check, url):
    """Download a Sentinel-1 Product. It just needs your SciHub user and password
    and the id of the product you want to download.
    """
    api = SentinelAPI(user, password, url)
    api.download(productid, path, check)
