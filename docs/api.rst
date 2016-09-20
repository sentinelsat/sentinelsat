.. _api:

Python API
==========

Quickstart
----------

.. code-block:: python

  # connect to the API
  from sentinelsat.sentinel import SentinelAPI, get_coordinates
  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and SciHub query keywords
  api.query(get_coordinates('map.geojson'), \
            "20151219", date(2015, 12, 29), \
            keywords={"platformname": "Sentinel-2", \
                      "cloudcoverpercentage": "[0 TO 30]"})

  # download all results from the search
  api.download_all()

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.get_footprints()

Valid search query keywords can be found at the `ESA SciHub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.


API
-----------

.. automodule:: sentinelsat.sentinel
    :members:
