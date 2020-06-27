"""
Handling of GeoJSON, geometries, WKT, etc. GIS-related functionality.
"""
from datetime import datetime

import geojson
import pytest

from sentinelsat import geojson_to_wkt, read_geojson, SentinelAPI


@pytest.mark.fast
def test_boundaries_latitude_more(fixture_path):
    with pytest.raises(ValueError):
        geojson_to_wkt(read_geojson(fixture_path("map_boundaries_lat.geojson")))


@pytest.mark.fast
def test_boundaries_longitude_less(fixture_path):
    with pytest.raises(ValueError):
        geojson_to_wkt(read_geojson(fixture_path("map_boundaries_lon.geojson")))


@pytest.mark.fast
def test_get_coordinates(fixture_path):
    wkt = (
        "POLYGON((-66.2695 -8.0592,-66.2695 0.7031,"
        "-57.3047 0.7031,-57.3047 -8.0592,-66.2695 -8.0592))"
    )
    assert geojson_to_wkt(read_geojson(fixture_path("map.geojson"))) == wkt
    assert geojson_to_wkt(read_geojson(fixture_path("map_z.geojson"))) == wkt
    assert geojson_to_wkt(read_geojson(fixture_path("map_nested.geojson"))) == wkt


@pytest.mark.vcr
@pytest.mark.scihub
def test_footprints_s1(api, test_wkt, read_fixture_file):
    products = api.query(
        test_wkt, (datetime(2014, 10, 10), datetime(2014, 12, 31)), producttype="GRD"
    )

    footprints = api.to_geojson(products)
    for footprint in footprints["features"]:
        assert not footprint["geometry"].errors()

    expected_footprints = geojson.loads(read_fixture_file("expected_search_footprints_s1.geojson"))
    # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
    assert set(footprints) == set(expected_footprints)


@pytest.mark.scihub
def test_footprints_s2(products, fixture_path):
    footprints = SentinelAPI.to_geojson(products)
    for footprint in footprints["features"]:
        assert not footprint["geometry"].errors()

    with open(fixture_path("expected_search_footprints_s2.geojson")) as geojson_file:
        expected_footprints = geojson.loads(geojson_file.read())
    # to compare unordered lists (JSON objects) they need to be sorted or changed to sets
    assert set(footprints) == set(expected_footprints)
