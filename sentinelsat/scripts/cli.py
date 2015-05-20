# Skeleton of a CLI

import click

import sentinelsat


@click.command('sentinel')
@click.argument('count', type=int, metavar='N')
def cli(count):
    """Echo a value `N` number of times"""
    for i in range(count):
        click.echo(sentinelsat.has_legs)
