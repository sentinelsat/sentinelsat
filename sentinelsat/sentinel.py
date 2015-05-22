# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import requests


def format_date(in_date):
    """Format date or datetime input to YYYY-MM-DDThh:mm:ssZ"""
    return in_date.strftime('%Y-%m-%dT%H:%M:%SZ')


class SentinelAPI(object):
    """Class to connect to Sentinel-1 Scientific Data Hub, search and download
    imagery.
    """
    def __init__(self, user, password):
        self.user = user
        self.password = password

    def query(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Call the Scihub"""
        self.format_url(area, initial_date, end_date, **keywords)
        self.content = requests.get(self.url, auth=(self.user, self.password))

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