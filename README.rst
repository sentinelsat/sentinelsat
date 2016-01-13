sentinelsat
============

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat

.. image:: https://travis-ci.org/ibamacsr/sentinelsat.svg
    :target: https://travis-ci.org/ibamacsr/sentinelsat

.. image:: https://coveralls.io/repos/ibamacsr/sentinelsat/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/ibamacsr/sentinelsat?branch=master


Utility pack to search and download Sentinel imagery from `Copernicus SciHub <https://scihub.copernicus.eu/>`_.


Installation
============

Sentinelsat depends on `homura <https://github.com/shichao-an/homura>`_, which depends on `PycURL <http://pycurl.sourceforge.net/>`_, so you need to install some dependencies on your system.

Ubuntu

.. code-block:: console

    sudo apt-get install build-essential libcurl4-openssl-dev python-dev python-pip

Fedora

.. code-block:: console

    sudo yum groupinstall "Development Tools"
    sudo yum install libcurl libcurl-devel python-devel python-pip

Windows

The easiest way to install pycurl is to use one of the `pycurl wheels <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl>`_ provided by Christoph Gohlke.

.. code-block:: console

    pip install pycurl.whl

Alternatively if you are using `Conda <http://conda.pydata.org/docs/>`_ you can do

.. code-block:: console

    conda install pycurl

Then install ``sentinelsat``:

.. code-block:: console

    pip install sentinelsat

Usage
=====

Sentinelsat provides a Python Library and a Command Line Interface to search and
download Sentinel products.

Command Line Interface
----------------------

Search
^^^^^^

.. code-block:: console

    sentinel search [OPTIONS] <user> <password> <geojson>

Search for Sentinel products and, optionally, download all the results.
Beyond your scihub username and password, you must pass a geojson file
containing the polygon of the area that you want to search in. If you
don't specify the start and end dates, it will search products published in the last 24
hours.

Examples:

.. code-block:: console

    sentinel search -d -s 20151219 -c 30 --md5 username password roi.geojson

Search and download all Sentinel-2 products with less than 30% cloud cover
acquired since 2015-12-19. Verify the integrity of the downloaded files with
the MD5 checksum provided by the Scihub.

.. code-block:: console

    sentinel search -f -s 20151219 -e 20151228 --sentinel1 -q "producttype=GRD,orbitdirection=Ascending" username password roi.geojson

Search all Sentinel-1 Ground Range Detected products acquired in Ascending orbit
between 2015-12-19 and 2015-12-28 and create a search_footprints.geojson so you
can compare the spatial coverage before downloading the scenes.


Options:

-s, --start TEXT  Start date of the query in the format YYYYMMDD.
-e, --end TEXT    End date of the query in the format YYYYMMDD.
-d, --download    Download all results of the query.
-f, --footprints  Create geojson file search_footprints.geojson with footprints
                  of the query result.
-p, --path PATH   Set the path where the files will be saved.
-q, --query TEXT  Extra search keywords you want to use in the query.
                  Separate keywords with comma.
                  Example: 'producttype=GRD,polarisationmode=HH'.
-u, --url TEXT    Define another API URL. Default URL is
                    'https://scihub.copernicus.eu/apihub/'.
--md5             Verify the MD5 checksum and write corrupt product ids and
                  filenames to corrupt_scenes.txt.
--sentinel1       Limit search to Sentinel-1 products.
--sentinel2       Limit search to Sentinel-2 products.
-c, --cloud INTEGER Maximum cloud cover in percent. (Automatically sets
                  --sentinel2)
--help            Show help message and exit.

Download
^^^^^^^^

.. code-block:: console

    sentinel download [OPTIONS] <user> <password> <productid>

Download a single Sentinel Product. Provide your scihub username and password and
the id of the product you want to download.


Example:

.. code-block:: console

    sentinel download --md5 -u "https://scihub.copernicus.eu/dhus/" username password a9048d1d-fea6-4df8-bedd-7bcb212be12e

Download the Sentinel-1 GRDH scene covering Santa Claus Village in Finland on
Christmas Eve 2015.

Options:

-p, --path PATH Set the path where the file will be saved.
-u, --url TEXT  Define another API URL. Default URL is
                    'https://scihub.copernicus.eu/apihub/'.
--md5           Verify the MD5 checksum and write corrupt product ids and
                filenames to corrupt_scenes.txt.


Python Library
--------------

Connect to the API:

.. code-block:: python

    from sentinelsat.sentinel import SentinelAPI
    api = SentinelAPI('user', 'password')

If you need to search or download data produced before November 16th, 2015, you must initialize `SentinelAPI` with the `api_url` parameter, setting it to use `https://scihub.copernicus.eu/dhus`.

.. code-block:: python

    api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

If you know the id of the product you want to download, you can download it by using:

.. code-block:: python

    api.download(<product_id>)

It is possible to hide the progress report, disable resume and auto_retry, and
pass any other keyword argument understood by the underlying homura library, e.g.:

.. code-block:: python

    api.download(<product_id>, show_progress=False, max_rst_retries=2)

You can also use the id to get information about the product, including id, title, size, footprint and download url:

.. code-block:: python

    api.get_product_info(<product_id>)

You can search products by specifying the coordinates of the area and a date interval:

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', '20150531', '20150612')

You can query by using date or datetime objects too.

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', datetime(2015, 5, 31, 12, 5), date(2015, 6, 12))

If you don't specify the start and end dates, it will query in the last 24 hours.

Beyond area and date parameters, you can use any search keywords accepted by the Scihub API, for example:

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', producttype='SLC')

You can also provide the search keywords as a dictionary:

.. code-block:: python

    api.query(get_coordinates(map.geojson), "20151219", "20151229", keywords={"platformname": "Sentinel-2", "cloudcoverpercentage": "[0 TO 30]"})

See the `SciHub User Guide <https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/3FullTextSearch#Search_Keywords>`_
for all the valid search keywords.

To download all the results of your query, use:

.. code-block:: python

    api.download_all()

To get a geojson FeatureCollection containing the footprints and metadata for the search results of the query, use:

.. code-block:: python

    api.get_footprints()

The download from Scihub will fail if the server certificate
cannot be verified because no default CA bundle is defined, as on Windows, or
when the CA bundle is outdated. In most cases the easiest solution is to
install or update `certifi <https://pypi.python.org/pypi/certifi>`_:

.. code-block:: console

    pip install -U certifi

You can also override the the path setting to the PEM file of the CA bundle using
the ``pass_through_opts`` keyword argument when calling ``api.download()`` or
``api.download_all()``:

.. code-block:: python

    from pycurl import CAINFO
    api.download_all(pass_through_opts={CAINFO: 'path/to/my/cacert.pem'})


Contributors
=============

* Wille Marcel
* Kersten Clauss
* Michele Citterio

License
=======

GPLv3+
