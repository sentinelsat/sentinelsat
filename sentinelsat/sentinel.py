# -*- coding: utf-8 -*-
from datetime import datetime
import requests


def format_date(in_date):
    return in_date.strftime('%Y-%m-%dT%H:%M:%SZ')


class Query(object):

    def __init__(self, area, initial_date=None, end_date=datetime.now()):

        ingestion_date = '(ingestionDate:[%s TO %s])' % (
            format_date(initial_date),
            format_date(end_date)
            )
        query_area = '(footprint:"Intersects(POLYGON((%s)))")' % area
        self.url = 'https://scihub.esa.int/dhus/search?format=xml&q=%s AND %s' \
            % (ingestion_date, query_area)