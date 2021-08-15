"""
Handling of GeoJSON, geometries, WKT, etc. GIS-related functionality.
"""
from datetime import datetime

import geojson
import pytest

from sentinelsat import geojson_to_wkt, read_geojson, SentinelAPI, placename_to_wkt


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
    wkt_single_collection = (
        "GEOMETRYCOLLECTION(POLYGON((-66.2695 -8.0592,-66.2695 0.7031,"
        "-57.3047 0.7031,-57.3047 -8.0592,-66.2695 -8.0592)))"
    )
    wkt_collection = (
        "GEOMETRYCOLLECTION("
        "POLYGON((9.2065 52.6164,9.8438 51.9849,10.7446 52.5630,"
        "9.8657 52.9751,9.2065 52.6164)),"
        "POLYGON((12.6123 52.9354,12.2388 52.4426,13.1396 52.2009,"
        "13.8647 52.5229,13.3374 52.8691,12.6123 52.9354))"
        ")"
    )
    assert geojson_to_wkt(read_geojson(fixture_path("map.geojson"))) == wkt_single_collection
    assert geojson_to_wkt(read_geojson(fixture_path("map_z.geojson"))) == wkt_single_collection
    assert geojson_to_wkt(read_geojson(fixture_path("map_nested.geojson"))) == wkt
    assert geojson_to_wkt(read_geojson(fixture_path("map_collection.geojson"))) == wkt_collection


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


@pytest.mark.vcr
@pytest.mark.scihub
def test_placename_to_wkt_valid():
    place_kwargs = ["florida", "ENVELOPE(-87.634896, -79.974306, 31.000968, 24.396308)"]
    # tests wkt response
    assert placename_to_wkt(place_kwargs[0])[0] == place_kwargs[1]


@pytest.mark.vcr
@pytest.mark.fast
def test_placename_to_wkt_invalid():
    # tests empty bbox exception in response to bad query
    with pytest.raises(ValueError) as e:
        wkt = placename_to_wkt("!@#$%^")
    assert 'Unable to find a matching location for "!@#$%^"' in str(e.value)
