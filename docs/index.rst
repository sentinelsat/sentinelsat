===========
Sentinelsat
===========

Sentinelsat makes finding and downloading `Copernicus Sentinel
<http://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Overview4>`_
satellite images from  the `Sentinels Scientific Datahub <https://scihub.copernicus.eu/>`_ easy.

It offers an easy to use command line interface.

.. code-block:: bash

  sentinel search --sentinel2 --cloud 30 user password search_polygon.geojson


and a powerful Python API.

.. code-block:: python

  from sentinelsat.sentinel import SentinelAPI, get_coordinates

  api = SentinelAPI('user', 'password')
  products = api.query(get_coordinates('search_polygon.geojson'), \
                     producttype = 'SLC', \
                     orbitdirection='ASCENDING')
  api.download_all(products)


Contents
^^^^^

.. toctree::
   :maxdepth: 2

   install
   cli
   api

Indices and tables
==================

  * :ref:`genindex`
  * :ref:`modindex`
  * :ref:`search`
