sentinelsat
===========

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat
    :alt: PyPI package

.. image:: https://travis-ci.com/sentinelsat/sentinelsat.svg?branch=master
    :target: https://travis-ci.com/sentinelsat/sentinelsat
    :alt: Travis-CI

.. image:: https://codecov.io/gh/sentinelsat/sentinelsat/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/sentinelsat/sentinelsat
    :alt: codecov.io code coverage

.. image:: https://readthedocs.org/projects/sentinelsat/badge/?version=stable
    :target: http://sentinelsat.readthedocs.io/en/stable/?badge=stable
    :alt: Documentation

.. image:: https://img.shields.io/badge/gitter-join_chat-1dce73.svg?logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4NCjxzdmcgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB4PSIwIiB5PSI1IiBmaWxsPSIjZmZmIiB3aWR0aD0iMSIgaGVpZ2h0PSI1Ii8%2BPHJlY3QgeD0iMiIgeT0iNiIgZmlsbD0iI2ZmZiIgd2lkdGg9IjEiIGhlaWdodD0iNyIvPjxyZWN0IHg9IjQiIHk9IjYiIGZpbGw9IiNmZmYiIHdpZHRoPSIxIiBoZWlnaHQ9IjciLz48cmVjdCB4PSI2IiB5PSI2IiBmaWxsPSIjZmZmIiB3aWR0aD0iMSIgaGVpZ2h0PSI0Ii8%2BPC9zdmc%2B&logoWidth=8
    :target: https://gitter.im/sentinelsat/
    :alt: gitter.im chat

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.595961.svg
   :target: https://doi.org/10.5281/zenodo.595961
   :alt: Zenodo DOI

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
  api.to_geodataframe(products)

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

  sentinelsat -u <user> -p <password> -g <search_polygon.geojson> -s 20150101 -e 20151231 -d \
  --producttype SLC -q "orbitdirection=Descending" \
  --url "https://scihub.copernicus.eu/dhus"

Username, password and DHuS URL can also be set via environment variables for convenience.

.. code-block:: bash
 
  # same result as query above
  export DHUS_USER="<user>"
  export DHUS_PASSWORD="<password>"
  export DHUS_URL="https://scihub.copernicus.eu/dhus"

  sentinelsat -g <search_polygon.geojson> -s 20150101 -e 20151231 -d \
  --producttype SLC -q "orbitdirection=Descending"

Options
^^^^^^^

+----+---------------+------+--------------------------------------------------------------------------------------------+
| -u | -\-user       | TEXT | Username [required] (or environment variable DHUS_USER)                                    |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -p | -\-password   | TEXT | Password [required] (or environment variable DHUS_PASSWORD)                                |
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
|    | -\-sentinel   | INT  | Limit search to a Sentinel satellite (constellation).                                      |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-instrument | TEXT | Limit search to a specific instrument on a Sentinel satellite.                             |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-producttype| TEXT | Limit search to a Sentinel product type.                                                   |
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
|    | -\-version    |      | Show version number and exit.                                                              |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -h | -\-help       |      | Show help message and exit.                                                                |
+----+---------------+------+--------------------------------------------------------------------------------------------+

Tests
=====

To run the tests on ``sentinelsat``:

.. code-block:: bash

    git clone https://github.com/sentinelsat/sentinelsat.git
    cd sentinelsat
    pip install -e .[dev]
    pytest -v

By default, prerecorded responses to Copernicus Open Access Hub queries are used to not be affected by its downtime.
To allow the tests to run actual queries against the Copernicus Open Access Hub set the environment variables

.. code-block:: bash

    export DHUS_USER=<username>
    export DHUS_PASSWORD=<password>

and add ``--disable-vcr`` to ``pytest`` arguments.
To update the recordings use ``--vcr-record`` with ``once``, ``new_episodes`` or ``all``. See `vcrpy docs <https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes>`_ for details.


Documentation
=============

To build the documentation:

.. code-block:: bash

    git clone https://github.com/sentinelsat/sentinelsat.git
    cd sentinelsat
    pip install -e .[dev]
    cd docs
    make html

The full documentation is also published at http://sentinelsat.readthedocs.io/.


Changelog
=========

See `CHANGELOG <CHANGELOG.rst>`_. You can also use GitHub's compare view to see the `changes in the master branch since last release <https://github.com/sentinelsat/sentinelsat/compare/v0.13...master>`_.

Contributors
============

We invite anyone to participate by contributing code, reporting bugs, fixing bugs, writing documentation and tutorials and discussing the future of this project. Please check `CONTRIBUTE.rst <CONTRIBUTE.rst>`_.

For a list of maintainers and contributors please see `AUTHORS.rst <AUTHORS.rst>`_ and the `contributor graph <https://github.com/sentinelsat/sentinelsat/graphs/contributors>`_.

License
=======

GPLv3+
