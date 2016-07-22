sentinelsat
============

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat

.. image:: https://travis-ci.org/ibamacsr/sentinelsat.svg
    :target: https://travis-ci.org/ibamacsr/sentinelsat

.. image:: https://coveralls.io/repos/ibamacsr/sentinelsat/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/ibamacsr/sentinelsat?branch=master
.. image:: https://sentinelsat.readthedocs.io/en/latest/?badge=latest
    :target: http://sentinelsat.readthedocs.io/


Sentinelsat makes finding and downloading `Copernicus Sentinel
<http://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Overview4>`_
satellite images easy.

It offers an easy to use command line interface.

.. code-block:: bash

  sentinel search --sentinel2 --cloud 30 user password search_polygon.geojson


and a powerfull Python API.

.. code-block:: python

  from sentinelsat.sentinel import SentinelAPI, get_coordinates

  api = SentinelAPI('user', 'password')
  api.query(
    get_coordinates("search_polygon.geojson"),
    producttype="SLC",
    orbitdirection="ASCENDING"
  )
  api.download_all()

Documentation is published at http://sentinelsat.readthedocs.io/.

Installation
============

Sentinelsat depends on `homura <https://github.com/shichao-an/homura>`_, which depends on `PycURL <http://pycurl.sourceforge.net/>`_, so you might need to install some dependencies on your system.

Install ``sentinelsat`` through pip:

.. code-block:: console

    pip install sentinelsat

The documentation contains examples on how to install the dependencies for `Ubuntu <https://sentinelsat.readthedocs.io/en/latest/install.html#ubuntu>`_, `Fedora <https://sentinelsat.readthedocs.io/en/latest/install.html#fedora>`_ and `Windows <https://sentinelsat.readthedocs.io/en/latest/install.html#windows>`_.

Usage
=====

Sentinelsat provides a Python Library and a Command Line Interface to search and
download Sentinel products.

Python Library
--------------

.. code-block:: python

  # connect to the API
  from sentinelsat.sentinel import SentinelAPI, get_coordinates
  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and SciHub query keywords
  api.query(get_coordinates(map.geojson), \
            "20151219", date(2015, 12, 29), \
            keywords={"platformname": "Sentinel-2", \
                      "cloudcoverpercentage": "[0 TO 30]"})

  # download all results from the search
  api.download_all()

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.get_footprints()

Valid search query keywords can be found at the `ESA SciHub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.

Command Line Interface
----------------------

A basic search query consists of a search polygon as well as the username and
password to access the Scihub.

.. code-block:: bash

  sentinel search [OPTIONS] <user> <password> <geojson>

Search areas are provided as GeoJSON polygons, which can be created with
`QGIS <http://qgis.org/en/site/>`_ or `geojson.io <http://geojson.io>`_.
If you do not specify a start and end date only products published in the last
24 hours will be queried.

Example
^^^^^^^

Search and download all Sentinel-1 scenes of type SLC, in descending
orbit for the year 2015.

.. code-block:: bash

  sentinel search -s 20150101 -e 20151231 -d \
  -q 'producttype=SLC, orbitdirection=Descending' \
  -u 'https://scihub.copernicus.eu/dhus' <user> <password> <poly.geojson>

Options
^^^^^^^

+----+--------------+------+--------------------------------------------------------------------------------------------+
| -s | -\-start     | TEXT | Start date of the query in the format YYYYMMDD.                                            |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -e | -\-end       | TEXT | End date of the query in the format YYYYMMDD.                                              |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -d | -\-download  |      | Download all results of the query.                                                         |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -f | -\-footprints|      | Create geojson file search_footprints.geojson with footprints of the query result.         |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -p | -\-path      | PATH | Set the path where the files will be saved.                                                |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -q | -\-query     | TEXT | Extra search keywords you want to use in the query. Separate keywords with comma.          |
|    |              |      | Example: 'producttype=GRD,polarisationmode=HH'.                                            |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -u | -\-url       | TEXT | Define another API URL. Default URL is 'https://scihub.copernicus.eu/apihub/'.             |
+----+--------------+------+--------------------------------------------------------------------------------------------+
|    | -\-md5       |      | Verify the MD5 checksum and write corrupt product ids and filenames to corrupt_scenes.txt. |
+----+--------------+------+--------------------------------------------------------------------------------------------+
|    | -\-sentinel1 |      | Limit search to Sentinel-1 products.                                                       |
+----+--------------+------+--------------------------------------------------------------------------------------------+
|    | -\-sentinel2 |      | Limit search to Sentinel-2 products.                                                       |
+----+--------------+------+--------------------------------------------------------------------------------------------+
| -c | -\-cloud     | INT  | Maximum cloud cover in percent. (Automatically sets --sentinel2)                           |
+----+--------------+------+--------------------------------------------------------------------------------------------+
|    | -\-help      |      | Show help message and exit.                                                                |
+----+--------------+------+--------------------------------------------------------------------------------------------+

Troubleshooting
===============

The download from Scihub will fail if the server certificate cannot be verified
because no default CA bundle is defined, as on Windows, or when the CA bundle is
outdated. In most cases the easiest solution is to install or update ``certifi``:

``pip install -U certifi``
You can also override the the path setting to the PEM file of the CA bundle
using the ``pass_through_opts`` keyword argument when calling ``api.download()``
or ``api.download_all()``:

.. code-block:: python

  from pycurl import CAINFO
  api.download_all(pass_through_opts={CAINFO: 'path/to/my/cacert.pem'})


Tests
======

To run the tests on `sentinelsat`:

.. code-block:: console

    git clone https://github.com/ibamacsr/sentinelsat.git
    cd sentinelsat
    pip install -e .[test]
    export SENTINEL_USER=<your scihub username>
    export SENTINEL_PASSWORD=<your scihub password>
    py.test -v


Contributors
=============

* Wille Marcel
* Kersten Clauss

License
=======

GPLv3+
