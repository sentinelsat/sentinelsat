sentinelsat
===========

.. image:: https://readthedocs.org/projects/sentinelsat/badge/?version=stable
    :target: http://sentinelsat.readthedocs.io/en/stable/?badge=stable
    :alt: Documentation

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat
    :alt: PyPI package

.. image:: https://github.com/sentinelsat/sentinelsat/actions/workflows/ci.yaml/badge.svg
    :target: https://github.com/sentinelsat/sentinelsat/actions
    :alt: GitHub Actions

.. image:: https://codecov.io/gh/sentinelsat/sentinelsat/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/sentinelsat/sentinelsat
    :alt: codecov.io code coverage

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.595961.svg
   :target: https://doi.org/10.5281/zenodo.595961
   :alt: Zenodo DOI

Sentinelsat makes searching, downloading and retrieving the metadata of `Sentinel
<http://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Overview4>`_
satellite images from the
`Copernicus Open Access Hub <https://scihub.copernicus.eu/>`_ easy.

It offers an easy-to-use command line interface

.. code-block:: bash

  sentinelsat -u <user> -p <password> --location Berlin --sentinel 2 --cloud 30 --start NOW-1MONTH

and a powerful Python API.

.. code-block:: python

  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt

  api = SentinelAPI('user', 'password')
  footprint = geojson_to_wkt(read_geojson('search_polygon.geojson'))
  products = api.query(footprint,
                       producttype='SLC',
                       orbitdirection='ASCENDING',
                       limit=10)
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

  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
  from datetime import date

  # connect to the API
  api = SentinelAPI('user', 'password', 'https://apihub.copernicus.eu/apihub')

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
  --url "https://apihub.copernicus.eu/apihub"

Username, password and DHuS URL can also be set via environment variables for convenience.

.. code-block:: bash
 
  # same result as query above
  export DHUS_USER="<user>"
  export DHUS_PASSWORD="<password>"
  export DHUS_URL="https://apihub.copernicus.eu/apihub"

  sentinelsat -g <search_polygon.geojson> -s 20150101 -e 20151231 -d \
  --producttype SLC -q "orbitdirection=Descending"

Options
^^^^^^^

.. list-table::

   * - -u
     - --user
     - TEXT
     - Username [required] (or environment variable DHUS_USER)
   * - -p
     - --password
     - TEXT
     - Password [required] (or environment variable DHUS_PASSWORD)
   * - 
     - --url
     - TEXT
     - Define another API URL. Default URL is 'https://apihub.copernicus.eu/apihub/'.
   * - -s
     - --start
     - TEXT
     - Start date of the query in the format YYYYMMDD or an expression like NOW-1DAY.
   * - -e
     - --end
     - TEXT
     - End date of the query.
   * - -g
     - --geometry
     - PATH
     - Search area geometry as GeoJSON file.
   * -  
     - --uuid
     - TEXT
     - Select a specific product UUID. Can be set more than once.
   * -  
     - --name
     - TEXT
     - Select specific product(s) by filename. Supports wildcards. Can be set more than once.
   * -  
     - --sentinel
     - INT
     - Limit search to a Sentinel satellite (constellation).
   * -  
     - --instrument
     - TEXT
     - Limit search to a specific instrument on a Sentinel satellite.
   * -  
     - --producttype
     - TEXT
     - Limit search to a Sentinel product type.
   * - -c
     - --cloud
     - INT
     - Maximum cloud cover in percent. (requires --sentinel to be 2 or 3)
   * - -o
     - --order-by
     - TEXT
     - Comma-separated list of keywords to order the result by. Prefix '-' for descending order.
   * - -l
     - --limit
     - INT
     - Maximum number of results to return. Defaults to no limit.
   * - -d
     - --download
     -  
     - Download all results of the query.
   * -
     - --fail-fast
     -
     - Skip all other other downloads if one fails.
   * -  
     - --path
     - PATH
     - Set the path where the files will be saved.
   * - -q
     - --query
     - TEXT
     - Extra search keywords you want to use in the query.
       Example: '-q producttype=GRD -q polarisationmode=HH'.
       Repeated keywords are interpreted as an "or" expression.
   * - -f
     - --footprints
     - FILENAME
     - Create a GeoJSON file at the provided path with footprints and metadata of the returned products. Set to '-' for stdout.
   * - 
     - --include-pattern
     - TEXT
     - Glob pattern to filter files (within each product) to be downloaded.
   * - 
     - --exclude-pattern
     - TEXT
     - Glob pattern to filter files (within each product) to be excluded from the downloaded.
   * -  
     - --timeout
     - FLOAT
     - How long to wait for a DataHub response (in seconds, default 60 sec).
   * -
     - --gnss
     -
     - Query orbit products form the GNSS end-point ("https://scihub.copernicus.eu/gnss").
   * -
     - --fmt
     - TEXT
     - Specify a custom format to print results. The format string shall be compatible with the Python "Format Specification Mini-Language".
   * -  
     - --info
     -  
     - Display DHuS server information.
   * -  
     - --version
     -  
     - Show version number and exit.
   * - 
     - --debug
     -  
     - Print debug log messages.
   * - -h
     - --help
     -  
     - Show help message and exit.

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

See `CHANGELOG <CHANGELOG.rst>`_. You can also use GitHub's compare view to see the `changes in the main branch since last release <https://github.com/sentinelsat/sentinelsat/compare/v1.1.1...main>`_.

Contributors
============

We invite anyone to participate by contributing code, reporting bugs, fixing bugs, writing documentation and tutorials and discussing the future of this project. Please check `CONTRIBUTE.rst <CONTRIBUTE.rst>`_.

For a list of maintainers and contributors please see `AUTHORS.rst <AUTHORS.rst>`_ and the `contributor graph <https://github.com/sentinelsat/sentinelsat/graphs/contributors>`_.

License
=======

GPLv3+
