"""
Tests for functionality related to the OpenSearch API of SciHub (https://scihub.copernicus.eu/apihub/search?...)
"""
from datetime import datetime, date, timedelta

import pytest

from sentinelsat import format_query_date, SentinelAPIError, SentinelAPI
from sentinelsat.sentinel import _format_order_by


@pytest.mark.vcr
@pytest.mark.scihub
def test_format_date(api):
    assert format_query_date(datetime(2015, 1, 1)) == "2015-01-01T00:00:00Z"
    assert format_query_date(date(2015, 1, 1)) == "2015-01-01T00:00:00Z"
    assert format_query_date("2015-01-01T00:00:00Z") == "2015-01-01T00:00:00Z"
    assert format_query_date("20150101") == "2015-01-01T00:00:00Z"
    assert format_query_date(" NOW ") == "NOW"
    assert format_query_date(None) == "*"

    for date_str in (
        "NOW",
        "NOW-1DAY",
        "NOW-1DAYS",
        "NOW-500DAY",
        "NOW-500DAYS",
        "NOW-2MONTH",
        "NOW-2MONTHS",
        "NOW-20MINUTE",
        "NOW-20MINUTES",
        "NOW+10HOUR",
        "2015-01-01T00:00:00Z+1DAY",
        "NOW+3MONTHS-7DAYS/DAYS",
        "*",
    ):
        assert format_query_date(date_str) == date_str
        api.query(raw="ingestiondate:[{} TO *]".format(date_str), limit=0)

    for date_str in (
        "NOW - 1HOUR",
        "NOW -   1HOURS",
        "NOW-1 HOURS",
        "NOW-1",
        "NOW-",
        "**",
        "+",
        "-",
    ):
        with pytest.raises(ValueError):
            format_query_date(date_str)
        with pytest.raises(SentinelAPIError):
            api.query(raw="ingestiondate:[{} TO *]".format(date_str), limit=0)


@pytest.mark.vcr
@pytest.mark.scihub
def test_SentinelAPI_connection(api, small_query):
    api.query(**small_query)
    assert api._last_query == (
        "beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z] "
        'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'
    )
    assert api._last_response.status_code == 200


@pytest.mark.vcr
@pytest.mark.scihub
def test_SentinelAPI_wrong_credentials(small_query):
    api = SentinelAPI("wrong_user", "wrong_password")
    with pytest.raises(SentinelAPIError) as excinfo:
        api.query(**small_query)
    assert excinfo.value.response.status_code == 401

    with pytest.raises(SentinelAPIError) as excinfo:
        api.get_product_odata("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
    assert excinfo.value.response.status_code == 401

    with pytest.raises(SentinelAPIError) as excinfo:
        api.download("8df46c9e-a20c-43db-a19a-4240c2ed3b8b")
    assert excinfo.value.response.status_code == 401

    with pytest.raises(SentinelAPIError) as excinfo:
        api.download_all(["8df46c9e-a20c-43db-a19a-4240c2ed3b8b"])
    assert excinfo.value.response.status_code == 401


@pytest.mark.fast
def test_api_query_format():
    wkt = "POLYGON((0 0,1 1,0 1,0 0))"

    now = datetime.now()
    last_24h = format_query_date(now - timedelta(hours=24))
    query = SentinelAPI.format_query(wkt, (last_24h, now))
    assert (
        query
        == "beginPosition:[%s TO %s] " % (last_24h, format_query_date(now))
        + 'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'
    )

    query = SentinelAPI.format_query(wkt, date=(last_24h, "NOW"), producttype="SLC", raw="IW")
    assert (
        query
        == "beginPosition:[%s TO NOW] " % (format_query_date(last_24h))
        + 'producttype:SLC IW footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'
    )

    query = SentinelAPI.format_query(wkt, producttype="SLC", raw="IW")
    assert query == 'producttype:SLC IW footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'

    query = SentinelAPI.format_query(area=None, date=None)
    assert query == ""

    query = SentinelAPI.format_query()
    assert query == ""

    query = SentinelAPI.format_query(raw="test")
    assert query == "test"


@pytest.mark.fast
def test_api_query_format_with_duplicates():
    with pytest.raises(ValueError) as excinfo:
        SentinelAPI.format_query(date=("NOW-1DAY", "NOW"), beginPosition=("NOW-3DAY", "NOW"))
    assert "duplicate" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        SentinelAPI.format_query(
            ingestiondate=("NOW-1DAY", "NOW"), ingestionDate=("NOW-3DAY", "NOW")
        )
    assert "duplicate" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        SentinelAPI.format_query(area="POINT(0, 0)", footprint="POINT(0, 0)")
    assert "duplicate" in str(excinfo.value)


@pytest.mark.fast
def test_api_query_format_ranges():
    query = SentinelAPI.format_query(cloudcoverpercentage=(0, 30))
    assert query == "cloudcoverpercentage:[0 TO 30]"

    query = SentinelAPI.format_query(cloudcoverpercentage=[0, 30])
    assert query == "cloudcoverpercentage:[0 TO 30]"

    query = SentinelAPI.format_query(cloudcoverpercentage=[None, 30])
    assert query == "cloudcoverpercentage:[* TO 30]"

    query = SentinelAPI.format_query(orbitnumber=(16302, None))
    assert query == "orbitnumber:[16302 TO *]"

    query = SentinelAPI.format_query(orbitnumber=(16302, "*"))
    assert query == "orbitnumber:[16302 TO *]"

    for value in [(None, None), ("*", None), (None, "*"), ("*", "*")]:
        query = SentinelAPI.format_query(orbitnumber=value)
        assert query == ""

    with pytest.raises(ValueError):
        SentinelAPI.format_query(cloudcoverpercentage=[])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(cloudcoverpercentage=[0])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(cloudcoverpercentage=[0, 1, 2])


@pytest.mark.fast
def test_api_query_format_sets():
    query = SentinelAPI.format_query(orbitnumber={16301, 16302, 16303})
    assert query == "orbitnumber:(16301 OR 16302 OR 16303)"

    query = SentinelAPI.format_query(ingestiondate={date(2017, 1, 1), "20170203"})
    assert query == "ingestiondate:(2017-01-01T00:00:00Z OR 2017-02-03T00:00:00Z)"


@pytest.mark.fast
def test_api_query_format_dates():
    query = SentinelAPI.format_query(ingestiondate=("NOW-1DAY", "NOW"))
    assert query == "ingestiondate:[NOW-1DAY TO NOW]"

    query = SentinelAPI.format_query(ingestiondate=(date(2017, 1, 1), "20170203"))
    assert query == "ingestiondate:[2017-01-01T00:00:00Z TO 2017-02-03T00:00:00Z]"

    query = SentinelAPI.format_query(ingestiondate="[NOW-1DAY TO NOW]")
    assert query == "ingestiondate:[NOW-1DAY TO NOW]"

    query = SentinelAPI.format_query(ingestiondate=[None, "NOW"])
    assert query == "ingestiondate:[* TO NOW]"

    for value in [(None, None), ("*", None), (None, "*"), ("*", "*")]:
        query = SentinelAPI.format_query(ingestiondate=value)
        assert query == ""

    with pytest.raises(ValueError):
        SentinelAPI.format_query(date="NOW")

    with pytest.raises(ValueError):
        SentinelAPI.format_query(date=["NOW"])

    with pytest.raises(ValueError):
        SentinelAPI.format_query(ingestiondate=[])


@pytest.mark.vcr
@pytest.mark.scihub
def test_api_query_format_escape_spaces(api):
    query = SentinelAPI.format_query(ingestiondate=("NOW-1DAY", "NOW"))
    assert query == "ingestiondate:[NOW-1DAY TO NOW]"

    query = SentinelAPI.format_query(ingestiondate="[NOW-1DAY TO NOW]")
    assert query == "ingestiondate:[NOW-1DAY TO NOW]"

    query = SentinelAPI.format_query(ingestiondate=" [NOW-1DAY TO NOW] ")
    assert query == "ingestiondate:[NOW-1DAY TO NOW]"

    query = SentinelAPI.format_query(relativeorbitnumber=" {101 TO 103} ")
    assert query == "relativeorbitnumber:{101 TO 103}"

    query = SentinelAPI.format_query(filename="S3A_OL_2* ")
    assert query == "filename:S3A_OL_2*"

    query = SentinelAPI.format_query(timeliness="Non Time Critical")
    assert query == r"timeliness:Non\ Time\ Critical"

    query = SentinelAPI.format_query(timeliness="Non\tTime\tCritical")
    assert query == r"timeliness:Non\ Time\ Critical"

    assert api.count(timeliness="Non Time Critical") > 0

    # Allow for regex weirdness
    query = SentinelAPI.format_query(timeliness=".+ Critical")
    assert query == r"timeliness:.+\ Critical"
    assert api.count(timeliness=".+ Critical") > 0

    query = SentinelAPI.format_query(identifier="/S[123 ]A.*/")
    assert query == r"identifier:/S[123 ]A.*/"
    assert api.count(identifier="/S[123 ]A.*/") > 0


@pytest.mark.vcr
@pytest.mark.scihub
def test_invalid_query(api):
    with pytest.raises(SentinelAPIError):
        api.query(raw="xxx:yyy")


@pytest.mark.fast
def test_format_url(api):
    start_row = 0
    url = api._format_url(offset=start_row)
    assert (
        url
        == "https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}".format(
            rows=api.page_size, start=start_row
        )
    )
    limit = 50
    url = api._format_url(limit=limit, offset=start_row)
    assert (
        url
        == "https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}".format(
            rows=limit, start=start_row
        )
    )
    url = api._format_url(limit=api.page_size + 50, offset=start_row)
    assert (
        url
        == "https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}".format(
            rows=api.page_size, start=start_row
        )
    )
    url = api._format_url(order_by="beginposition desc", limit=api.page_size + 50, offset=10)
    assert (
        url == "https://scihub.copernicus.eu/apihub/search?format=json&rows={rows}&start={start}"
        "&orderby={orderby}".format(rows=api.page_size, start=10, orderby="beginposition desc")
    )


@pytest.mark.fast
def test_format_url_custom_api_url():
    api = SentinelAPI("user", "pw", api_url="https://scihub.copernicus.eu/dhus/")
    url = api._format_url()
    assert url.startswith("https://scihub.copernicus.eu/dhus/search")

    api = SentinelAPI("user", "pw", api_url="https://scihub.copernicus.eu/dhus")
    url = api._format_url()
    assert url.startswith("https://scihub.copernicus.eu/dhus/search")


@pytest.mark.fast
def test_format_order_by():
    res = _format_order_by("cloudcoverpercentage")
    assert res == "cloudcoverpercentage asc"

    res = _format_order_by("+cloudcoverpercentage,-beginposition")
    assert res == "cloudcoverpercentage asc,beginposition desc"

    res = _format_order_by(" +cloudcoverpercentage, -beginposition ")
    assert res == "cloudcoverpercentage asc,beginposition desc"

    with pytest.raises(ValueError):
        _format_order_by("+cloudcoverpercentage-beginposition")


@pytest.mark.vcr
@pytest.mark.scihub
def test_small_query(api, small_query):
    api.query(**small_query)
    assert api._last_query == (
        "beginPosition:[2015-01-01T00:00:00Z TO 2015-01-02T00:00:00Z] "
        'footprint:"Intersects(POLYGON((0 0,1 1,0 1,0 0)))"'
    )
    assert api._last_response.status_code == 200


@pytest.mark.vcr(decode_compressed_response=False)
@pytest.mark.scihub
def test_large_query(api, large_query):
    full_products = list(api.query(**large_query))
    assert api._last_query == (
        "beginPosition:[2015-12-01T00:00:00Z TO 2015-12-31T00:00:00Z] "
        'footprint:"Intersects(POLYGON((0 0,0 10,10 10,10 0,0 0)))"'
    )
    assert api._last_response.status_code == 200
    assert len(full_products) > api.page_size

    result = list(api.query(limit=150, **large_query))
    assert result == full_products[:150]

    result = list(api.query(limit=20, offset=90, **large_query))
    assert result == full_products[90:110]

    result = list(api.query(limit=20, offset=len(full_products) - 10, **large_query))
    assert result == full_products[-10:]


@pytest.mark.vcr
@pytest.mark.scihub
def test_count(api):
    count = api.count(None, ("20150101", "20151231"))
    assert count > 100000


@pytest.mark.vcr
@pytest.mark.scihub
def test_too_long_query(api):
    # Test whether our limit calculation is reasonably correct and
    # that a relevant error message is provided

    def create_query(n):
        return " a_-.*:,?+~!" * n

    # Expect no error
    q = create_query(163)
    assert 0.99 < SentinelAPI.check_query_length(q) < 1.0
    with pytest.raises(SentinelAPIError) as excinfo:
        api.count(raw=q)
    assert "Invalid query string" in excinfo.value.msg

    # Expect HTTP status 500 Internal Server Error
    q = create_query(164)
    assert 0.999 <= SentinelAPI.check_query_length(q) < 1.01
    with pytest.raises(SentinelAPIError) as excinfo:
        api.count(raw=q)
    assert excinfo.value.response.status_code == 500
    assert (
        "Request Entity Too Large" in excinfo.value.msg
        or "Request-URI Too Long" in excinfo.value.msg
    )


@pytest.mark.vcr
@pytest.mark.scihub
def test_date_arithmetic(api):
    products = api.query(
        "ENVELOPE(0, 1, 1, 0)", ("2016-12-01T00:00:00Z-1DAY", "2016-12-01T00:00:00Z+1DAY-1HOUR")
    )
    assert api._last_response.status_code == 200
    assert 0 < len(products) < 30


@pytest.mark.vcr
@pytest.mark.scihub
def test_quote_symbol_bug(api):
    # A test to check if plus symbol handling works correctly on the server side
    # It used to raise an error but has since been fixed
    # https://github.com/SentinelDataHub/DataHubSystem/issues/23

    q = "beginposition:[2017-05-30T00:00:00Z TO 2017-05-31T00:00:00Z+1DAY]"
    count = api.count(raw=q)
    assert count > 0


@pytest.mark.vcr
@pytest.mark.scihub
def test_s2_cloudcover(api, test_wkt):
    products = api.query(
        test_wkt, ("20181212", "20181228"), platformname="Sentinel-2", cloudcoverpercentage=(0, 10)
    )

    product_ids = list(products)
    assert product_ids == [
        "bf652bc4-299c-4c39-9238-ee5a3fdc0d3e",
        "b508a8cd-c7d6-4a4d-9286-6d9463926554",
        "c9b0a744-c0e5-41f9-af6c-f0af83681e58",
        "2e69293b-591f-41d4-99e5-89ec087ae487",
        "dcd0849f-f43a-46f4-9267-da8069b74dd8",
    ]

    # For order-by test
    vals = [x["cloudcoverpercentage"] for x in products.values()]
    assert sorted(vals) != vals
    assert all(0 <= x <= 10 for x in vals)


@pytest.mark.vcr
@pytest.mark.scihub
def test_order_by(api, test_wkt):
    kwargs = dict(
        area=test_wkt,
        date=("20151219", "20160519"),
        platformname="Sentinel-2",
        cloudcoverpercentage=(0, 10),
        order_by="cloudcoverpercentage, -beginposition",
    )
    # Check that order_by works correctly also in cases where pagination is required
    expected_count = api.count(**kwargs)
    assert 100 < expected_count < 250
    products = api.query(**kwargs)
    assert len(products) == expected_count
    vals = [x["cloudcoverpercentage"] for x in products.values()]
    assert sorted(vals) == vals
    assert all(0 <= x <= 10 for x in vals)


@pytest.mark.vcr
@pytest.mark.scihub
def test_area_relation(api):
    params = dict(
        area="POLYGON((10.83 53.04,11.64 53.04,11.64 52.65,10.83 52.65,10.83 53.04))",
        date=("20151219", "20151226"),
    )
    result = api.query(**params)
    n_intersects = len(result)
    assert n_intersects > 10

    result = api.query(area_relation="contains", **params)
    n_contains = len(result)
    assert 0 < n_contains < n_intersects
    result = api.query(area_relation="IsWithin", **params)
    n_iswithin = len(result)
    assert n_iswithin == 0

    # Check that unsupported relations raise an error
    with pytest.raises(ValueError):
        api.query(area_relation="disjoint", **params)


@pytest.mark.vcr
@pytest.mark.scihub
def test_query_by_names(api, smallest_online_products):
    names = [product["title"] for product in smallest_online_products]
    expected = {product["title"]: {product["id"]} for product in smallest_online_products}

    result = api._query_names(names)
    assert list(result) == names
    for name in names:
        assert set(result[name]) == expected[name]

    result2 = api._query_names(names * 100)
    assert result == result2
