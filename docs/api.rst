.. _api:

Python API
==========

Quickstart
----------

.. code-block:: python

  # connect to the API
  from sentinelsat.sentinel import SentinelAPI, get_coordinates
  from datetime import date
  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and SciHub query keywords
  api.query(get_coordinates('map.geojson'), \
            '20151219', date(2015, 12, 29), \
            platformname = 'Sentinel-2', \
            cloudcoverpercentage = '[0 TO 30]'})

  # download all results from the search
  api.download_all()

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.get_footprints()

Valid search query keywords can be found at the `ESA SciHub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.


Logging
-------

Sentinelsat logs to ``sentinelsat`` and the API to ``sentinelsat.SentinelAPI``.

There is no predefined `logging<https://docs.python.org/3/library/logging.html>`_ handler, 
so in order to have your script print the log messages, either use ``logging.baseConfig``

.. code-block:: python

  import logging

  logging.basicConfig(format='%(message)s', level='INFO')


or add a custom handler for ``sentinelsat``

.. code-block:: python

  import logging

  logger = logging.getLogger('sentinelsat')
  logger.setLevel('INFO')

  h = logging.StreamHandler()
  h.setLevel('INFO')
  fmt = logging.Formatter('%(message)s')
  h.setFormatter(fmt)
  logger.addHandler(h)


API
-----------

.. automodule:: sentinelsat.sentinel
    :members:
