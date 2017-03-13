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
  products = api.query(get_coordinates('map.geojson'), \
                       '20151219', date(2015, 12, 29), \
                       platformname = 'Sentinel-2', \
                       cloudcoverpercentage = '[0 TO 30]')

  # download all results from the search
  api.download_all(products)

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.to_geojson(products)

Valid search query keywords can be found at the `ESA SciHub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.


Logging
-------

Sentinelsat logs to ``sentinelsat`` and the API to ``sentinelsat.SentinelAPI``.

There is no predefined `logging <https://docs.python.org/3/library/logging.html>`_ handler,
so in order to have your script print the log messages, either use ``logging.baseConfig``

.. code-block:: python

  import logging

  logging.basicConfig(format='%(message)s', level='INFO')


or add a custom handler for ``sentinelsat`` (as implemented in ``cli.py``)

.. code-block:: python

  import logging

  logger = logging.getLogger('sentinelsat')
  logger.setLevel('INFO')

  h = logging.StreamHandler()
  h.setLevel('INFO')
  fmt = logging.Formatter('%(message)s')
  h.setFormatter(fmt)
  logger.addHandler(h)


Sorting & Filtering
-------------------

In addition to the `search query keywords <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ sentinelsat allows
filtering and sorting of search results before download. To simplify these operations sentinelsat offers the convenience
functions ``to_dict()``, ``to_geojson()``, ``to_dataframe()`` and ``to_geodataframe()`` which return the search results as a Python dictionary,
a Pandas DataFrame or a GeoPandas GeoDataFrame, respectively. ``to_dataframe()`` and ``to_geodataframe()`` require ``Pandas``
and ``GeoPandas`` to be installed, respectively.

In this example we query Sentinel-2 scenes over a location and convert the query results to a Pandas DataFrame. The DataFrame is then sorted by cloud cover
and ingestiondate. We limit the query to first 5 results within our timespan and download them, starting with the least cloudy scene. Filtering can be done with
all data types, as long as you pass the ``id`` to the download function.

.. code-block:: python

  # connect to the API
  from sentinelsat.sentinel import SentinelAPI, get_coordinates
  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # search by polygon, time, and SciHub query keywords
  products = api.query(get_coordinates('map.geojson'), \
                       '20151219', date(2015, 12, 29), \
                       platformname = 'Sentinel-2')

  # convert to Pandas DataFrame
  products_df = api.to_dataframe(products)

  # sort and limit to first 5 sorted products
  products_df_sorted = products_df.sort_values(['cloudcoverpercentage', 'ingestiondate'], ascending=[True, True])
  products_df_sorted = products_df_sorted.head(5)

  # download sorted and reduced products in order
  for product_id in products_df_sorted["id"]:
    api.download(product_id)


API
-----------

.. automodule:: sentinelsat.sentinel
    :members:
