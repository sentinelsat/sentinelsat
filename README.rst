sentinelsat
===========

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat

.. image:: https://travis-ci.org/sentinelsat/sentinelsat.svg
    :target: https://travis-ci.org/sentinelsat/sentinelsat

.. image:: https://codecov.io/gh/sentinelsat/sentinelsat/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/sentinelsat/sentinelsat

.. image:: https://readthedocs.org/projects/sentinelsat/badge/?version=master
    :target: http://sentinelsat.readthedocs.io/en/master/?badge=master
    :alt: Documentation

.. image:: https://img.shields.io/badge/gitter-join_chat-1dce73.svg?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4NCjxzdmcgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB4PSIwIiB5PSI1IiBmaWxsPSIjZmZmIiB3aWR0aD0iMSIgaGVpZ2h0PSI1Ii8%2BPHJlY3QgeD0iMiIgeT0iNiIgZmlsbD0iI2ZmZiIgd2lkdGg9IjEiIGhlaWdodD0iNyIvPjxyZWN0IHg9IjQiIHk9IjYiIGZpbGw9IiNmZmYiIHdpZHRoPSIxIiBoZWlnaHQ9IjciLz48cmVjdCB4PSI2IiB5PSI2IiBmaWxsPSIjZmZmIiB3aWR0aD0iMSIgaGVpZ2h0PSI0Ii8%2BPC9zdmc%2B&logoWidth=8
    :target: https://gitter.im/sentinelsat/
    :alt: gitter.im chat

.. image:: https://zenodo.org/badge/36093931.svg
   :target: https://zenodo.org/badge/latestdoi/36093931


Sentinelsat makes searching, downloading and retrieving the metadata of `Sentinel
<http://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Overview4>`_
satellite images from the
`Copernicus Open Access Hub <https://scihub.copernicus.eu/>`_ easy.

It offers an easy-to-use command line interface

.. code-block:: bash

  sentinelsat -u <user> -p <password> -g <search_polygon.geojson> --sentinel 2 --cloud 30

and a powerful Python API.

.. code-block:: python

  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt

  api = SentinelAPI('user', 'password')
  footprint = geojson_to_wkt(read_geojson('search_polygon.geojson'))
  products = api.query(footprint,
                       producttype='SLC',
                       orbitdirection='ASCENDING')
  api.download_all(products)



Documentation is published at http://sentinelsat.readthedocs.io/.

Installation
============

Install ``sentinelsat`` through pip:

.. code-block:: bash

    pip install sentinelsat

Usage
=====

Sentinelsat provides a Python API and a command line interface to search,
download and retrieve the metadata for Sentinel products.

Python Library
--------------

.. code-block:: python
  
  from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
  from datetime import date

  # connect to the API
  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and Hub query keywords
  footprint = geojson_to_wkt(read_geojson('map.geojson'))
  products = api.query(footprint,
                       date = ('20151219', date(2015, 12, 29)),
                       platformname = 'Sentinel-2',
                       cloudcoverpercentage = (0, 30))

  # download all results from the search
  api.download_all(products)

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.to_geojson(products)

  # GeoPandas GeoDataFrame with the metadata of the scenes and the footprints as geometries
  api.to_geopandas(products)

  # Get basic information about the product: its title, file size, MD5 sum, date, footprint and
  # its download url
  api.get_product_odata(<product_id>)

  # Get the product's full metadata available on the server
  api.get_product_odata(<product_id>, full=True)

Valid search query keywords can be found at the `Copernicus Open Access Hub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.

Command Line Interface
----------------------

A basic search query consists of a search area geometry as well as the username and
password to access the Copernicus Open Access Hub.

.. code-block:: bash

  sentinelsat -u <user> -p <password> -g <geojson>

Search areas are provided as GeoJSON files, which can be created with
`QGIS <http://qgis.org/en/site/>`_ or `geojson.io <http://geojson.io>`_.
If you do not specify a start and end date only products published in the last
24 hours will be queried.

Example
^^^^^^^

Search and download all Sentinel-1 scenes of type SLC, in descending
orbit, for the year 2015.

.. code-block:: bash

  sentinelsat -u <user> -p <password> --area search_polygon.geojson -s 20150101 -e 20151231 -d \
  --producttype SLC -q "orbitdirection=Descending" \
  --url "https://scihub.copernicus.eu/dhus"

Options
^^^^^^^

+----+---------------+------+--------------------------------------------------------------------------------------------+
| -u | -\-user       | TEXT | Username [required]                                                                        |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -p | -\-password   | TEXT | Password [required]                                                                        |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-url        | TEXT | Define another API URL. Default URL is 'https://scihub.copernicus.eu/apihub/'.             |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -s | -\-start      | TEXT | Start date of the query in the format YYYYMMDD.                                            |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -e | -\-end        | TEXT | End date of the query in the format YYYYMMDD.                                              |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -g | -\-geometry   | PATH | Search area geometry as GeoJSON file.                                                      |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-uuid       | TEXT | Select a specific product UUID instead of a query. Multiple UUIDs can separated by commas. |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-name       | TEXT | Select specific product(s) by filename. Supports wildcards.                                |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-sentinel   |      | Limit search to a Sentinel satellite (constellation).                                      |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-instrument |      | Limit search to a specific instrument on a Sentinel satellite.                             |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-producttype|      | Limit search to a Sentinel product type.                                                   |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -c | -\-cloud      | INT  | Maximum cloud cover in percent. (requires --sentinel to be 2 or 3)                         |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -o | -\-order-by   | TEXT | Comma-separated list of keywords to order the result by. Prefix '-' for descending order.  |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -l | -\-limit      | INT  |  Maximum number of results to return. Defaults to no limit.                                |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -d | -\-download   |      | Download all results of the query.                                                         |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-path       | PATH | Set the path where the files will be saved.                                                |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -q | -\-query      | TEXT | Extra search keywords you want to use in the query. Separate keywords with comma.          |
|    |               |      | Example: 'producttype=GRD,polarisationmode=HH'.                                            |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -f | -\-footprints |      | Create geojson file search_footprints.geojson with footprints of the query result.         |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-md5        |      | Verify the MD5 checksum and write corrupt product ids and filenames to corrupt_scenes.txt. |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-version    |      | Show version number and exit.                                                              |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-help       |      | Show help message and exit.                                                                |
+----+---------------+------+--------------------------------------------------------------------------------------------+

Tests
=====

To run the tests on ``sentinelsat``:

.. code-block:: bash

    git clone https://github.com/sentinelsat/sentinelsat.git
    cd sentinelsat
    pip install -e .[test]
    py.test -v

By default, prerecorded responses to Copernicus Open Access Hub queries are used to not be affected by its downtime.
To allow the tests to run actual queries against the Copernicus Open Access Hub set the environment variables

.. code-block:: bash

    export SENTINEL_USER=<username>
    export SENTINEL_PASSWORD=<password>

and add ``--vcr disable`` to ``py.test`` arguments.
To update the recordings use either ``--vcr record_new`` or ``--vcr reset``.

Documentation
=============

To build the documentation:

.. code-block:: bash

    git clone https://github.com/sentinelsat/sentinelsat.git
    cd sentinelsat
    pip install -e .[docs]
    cd docs
    make html

The full documentation is also published at http://sentinelsat.readthedocs.io/.


Changelog
=========

See `CHANGELOG <CHANGELOG.rst>`_. You can also use Githubs compare view to see the `changes since last release <https://github.com/sentinelsat/sentinelsat/compare/v0.12...master>`_.

Contributors
============

* Wille Marcel
* Kersten Clauss
* Martin Valgur
* Jonas Sølvsteen
* Luca Delucchi

We invite anyone to participate by contributing code, reporting bugs, fixing bugs, writing documentation and tutorials and discussing the future of this project. Please check `CONTRIBUTE.rst <CONTRIBUTE.rst>`_.

License
=======

GPLv3+
