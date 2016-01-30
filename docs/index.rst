===========
Sentinelsat
===========

Sentinelsat makes finding and downloading Copernicus Sentinel satellite
images easy.

It offers a powerfull Python API

.. code-block:: python

  from sentinelsat.sentinel import SentinelAPI, get_coordinates

  api = SentinelAPI('user', 'password')
  api.query(
    get_coordinates("search_polygon.geojson"),
    producttype="SLC"
  )
  api.download_all()

and an easy to use command line interface.

.. code-block:: bash

  sentinel search -q "producttype=SLC" user password search_polygon.geojson


Guide
^^^^^

.. toctree::
   :maxdepth: 2



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
