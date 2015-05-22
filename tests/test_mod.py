from datetime import datetime, date, timedelta
from os import environ

from sentinelsat.sentinel import SentinelAPI, format_date


def test_format_date():
    assert format_date(datetime(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_date(date(2015, 1, 1)) == '2015-01-01T00:00:00Z'


def test_SentinelAPI():
    api = SentinelAPI(
        environ.get('SENTINEL_USER'),
        environ.get('SENTINEL_PASSWORD')
    )
    api.query('0 0,1 1,0 1,0 0', datetime(2015, 1, 1), datetime(2015, 1, 2))

    assert api.url == 'https://scihub.esa.int/dhus/search?format=json' + \
        '&q=(ingestionDate:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z]) ' + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'
    assert api.content.status_code == 200

    now = datetime.now()
    api.format_url('0 0,1 1,0 1,0 0', end_date=now)
    last_24h = format_date(now - timedelta(hours=24))
    assert api.url == 'https://scihub.esa.int/dhus/search?format=json' + \
        '&q=(ingestionDate:[%s TO %s]) ' % (last_24h, format_date(now)) + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'

    api.format_url('0 0,1 1,0 1,0 0', end_date=now, producttype='SLC')
    assert api.url == 'https://scihub.esa.int/dhus/search?format=json' + \
        '&q=(ingestionDate:[%s TO %s]) ' % (last_24h, format_date(now)) + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))") ' + \
        'AND (producttype:SLC)'
