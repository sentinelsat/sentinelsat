# -*- coding: utf-8 -*-
from homura import download

from datetime import datetime, timedelta
from os.path import join

import requests


def format_date(in_date):
    """Format date or datetime input to YYYY-MM-DDThh:mm:ssZ"""
    return in_date.strftime('%Y-%m-%dT%H:%M:%SZ')


class SentinelAPI(object):
    """Class to connect to Sentinel-1 Scientific Data Hub, search and download
    imagery.
    """
    def __init__(self, user, password):
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.get('https://scihub.esa.int/dhus/odata/v1/$metadata')

    def query(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Call the Scihub"""
        self.format_url(area, initial_date, end_date, **keywords)
        self.content = self.session.get(self.url)

    def format_url(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Create the URL to access the SciHub API."""
        if initial_date is None:
            initial_date = end_date - timedelta(hours=24)

        ingestion_date = '(ingestionDate:[%s TO %s])' % (
            format_date(initial_date),
            format_date(end_date)
        )
        query_area = ' AND (footprint:"Intersects(POLYGON((%s)))")' % area

        filters = ''
        for kw in sorted(keywords.keys()):
            filters += ' AND (%s:%s)' % (kw, keywords[kw])

        self.url = 'https://scihub.esa.int/dhus/search?format=json&q=%s%s%s' \
            % (ingestion_date, query_area, filters)

    def get_products(self):
        """Return the ids of the products found in the Query."""
        try:
            self.products = self.content.json()['feed']['entry']
            return self.products
        except KeyError:
            print('No products found in this query.')
            return []

    def download(self, id, title=None, path='.'):
        url = "https://scihub.esa.int/dhus/odata/v1/Products('%s')/$value" % id
        if title is None:
            title = id
        path = join(path, title + '.zip')
        download(url, path=path, session=self.session)

    def download_all(self, path='.'):
        for product in self.get_products():
            self.download(product['id'], product['title'], path)