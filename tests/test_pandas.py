"""
Tests methods dealing with converting product info into pandas and geopandas formats.
"""
import sys

import pytest

from sentinelsat import SentinelAPI


@pytest.mark.pandas
@pytest.mark.fast
def test_missing_dependency_dataframe(monkeypatch):
    with pytest.raises(ImportError):
        monkeypatch.setitem(sys.modules, "pandas", None)
        SentinelAPI.to_dataframe({"test": "test"})


@pytest.mark.geopandas
@pytest.mark.fast
def test_missing_dependency_geodataframe(monkeypatch):
    with pytest.raises(ImportError):
        monkeypatch.setitem(sys.modules, "geopandas", None)
        SentinelAPI.to_geodataframe({"test": "tst"})


@pytest.mark.pandas
@pytest.mark.scihub
def test_to_pandas(products):
    df = SentinelAPI.to_dataframe(products)
    assert type(df).__name__ == "DataFrame"
    assert len(products) == len(df)
    assert set(products) == set(df.index)


@pytest.mark.pandas
@pytest.mark.fast
def test_to_pandas_empty():
    df = SentinelAPI.to_dataframe({})
    assert type(df).__name__ == "DataFrame"
    assert len(df) == 0


@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.scihub
def test_to_geopandas(products):
    gdf = SentinelAPI.to_geodataframe(products)
    assert type(gdf).__name__ == "GeoDataFrame"
    print(gdf.unary_union.area)
    assert gdf.unary_union.area == pytest.approx(89.6, abs=0.1)
    assert len(gdf) == len(products)
    assert gdf.crs == {"init": "epsg:4326"}


@pytest.mark.pandas
@pytest.mark.geopandas
@pytest.mark.fast
def test_to_geopandas_empty():
    gdf = SentinelAPI.to_geodataframe({})
    assert type(gdf).__name__ == "GeoDataFrame"
    assert len(gdf) == 0
