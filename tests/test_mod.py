from datetime import datetime, date

from sentinelsat.sentinel import Query, format_date


def test_format_date():
    assert format_date(datetime(2015, 1, 1)) == '2015-01-01T00:00:00Z'
    assert format_date(date(2015, 1, 1)) == '2015-01-01T00:00:00Z'

def test_query():
    area = '0 0,1 1,0 1,0 0'
    query = Query(area, datetime(2015, 1, 1), datetime(2015, 1, 2))
    expected_url = 'https://scihub.esa.int/dhus/search?format=xml' + \
        '&q=(ingestionDate:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z]) ' + \
        'AND (footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))")'
    assert query.url == expected_url
