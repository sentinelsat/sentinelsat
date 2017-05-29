===========
Sentinelsat
===========

Sentinelsat makes searching, downloading and retrieving the metadata of `Sentinel
<http://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Overview4>`_
satellite images from the
`Copernicus Open Access Hub <https://scihub.copernicus.eu/>`_ easy.

It offers an easy-to-use command line interface

.. code-block:: bash

  sentinel search --sentinel 2 --cloud 30 user password search_polygon.geojson

and a powerful Python API.

.. code-block:: python

  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt

  api = SentinelAPI('user', 'password')
  footprint = geojson_to_wkt(read_geojson('search_polygon.geojson'))
  products = api.query(footprint,
                       producttype='SLC',
                       orbitdirection='ASCENDING')
  api.download_all(products)


Contents
^^^^^^^^

.. toctree::
   :maxdepth: 2

   install
   cli
   api

.. toctree::
   :hidden:

   changelog

Indices and tables
==================

  * :ref:`genindex`
  * :ref:`modindex`
  * :ref:`search`
