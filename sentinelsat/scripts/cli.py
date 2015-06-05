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
    help='Start date of the query in the format YYYY-MM-DD.')
@click.option('--end', '-e', type=str, default='NOW',
    help='End date of the query in the format YYYY-MM-DD.')
@click.option('--download', '-d', is_flag=True,
    help='Download all the results of the query.')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where to save the file on.')
def search(user, password, geojson, start, end, download, path):
    """Search for Sentinel-1 products and, optionally, download all the results"""
    api = SentinelAPI(user, password)
    api.query(get_coordinates(geojson), start, end)
    if download is True:
        api.download_all(path)
    else:
        print((api.get_products()))


@cli.command()
@click.argument('user', type=str, metavar='<user>')
@click.argument('password', type=str, metavar='<password>')
@click.argument('productid', type=str, metavar='<productid>')
@click.option('--path', '-p', type=click.Path(exists=True), default='.',
    help='Set the path where to save the file on.')
def download(user, password, productid, path):
    """Download a Sentinel-1 Product."""
    api = SentinelAPI(user, password)
    api.download(productid, path)