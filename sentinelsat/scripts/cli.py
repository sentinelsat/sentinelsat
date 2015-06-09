import click

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
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where the files will be saved.')
def search(user, password, geojson, start, end, download, path):
    """Search for Sentinel-1 products and, optionally, download all the results.
    Beyond your scihub user and password, you must pass a geojson file
    containing the polygon of the area you want to search for. If you
    don't especify the start and end dates, it will search in the last 24 hours.
    """
    api = SentinelAPI(user, password)
    api.query(get_coordinates(geojson), start, end)
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
    """Download a Sentinel-1 Product. It just needs you scihub user and password
    and the id of the product you want to download.
    """
    api = SentinelAPI(user, password)
    api.download(productid, path)