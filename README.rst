sentinelsat
============

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat


Utility pack to search and download Sentinel-1 imagery from `ESA SciHub <https://scihub.esa.int/>`_.

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
download Sentinel-1 products.

Command Line Interface
----------------------

Search
^^^^^^

.. code-block:: console

    sentinel search [OPTIONS] <user> <password> <geojson>

Search for Sentinel-1 products and, optionally, download all the results.
Beyond your scihub username and password, you must pass a geojson file
containing the polygon of the area that you want to search in. If you
don't specify the start and end dates, it will search products published in the last 24
hours.

Options:

-s, --start TEXT  Start date of the query in the format YYYYMMDD.
-e, --end TEXT    End date of the query in the format YYYYMMDD.
-d, --download    Download all results of the query.
-f, --footprints   Create geojson file with footprints of the query result.
-p, --path PATH   Set the path where the files will be saved.
-q, --query TEXT  Extra search keywords you want to use in the query.
                  Separate keywords with comma.
                  Example: 'producttype=GRD,polarisationmode=HH'.
-u, --url TEXT    Define another API URL. Default URL is
                    'https://scihub.esa.int/apihub/'.

Download
^^^^^^^^

.. code-block:: console

    sentinel download [OPTIONS] <user> <password> <productid>

Download a single Sentinel-1 Product. Provide your scihub username and password and
the id of the product you want to download.

Options:

-p, --path PATH  Set the path where the file will be saved.
-u, --url TEXT    Define another API URL. Default URL is
                    'https://scihub.esa.int/apihub/'.


Python Library
--------------

Connect to the API:

.. code-block:: python

    from sentinelsat.sentinel import SentinelAPI
    api = SentinelAPI('user', 'password')

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

Beyond area and date parameters, you can use any search keywords accepted by the scihub API, for example:

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', producttype='SLC')

See the `SciHub User Guide <https://scihub.esa.int/twiki/do/view/SciHubUserGuide/3FullTextSearch#Search_Keywords>`_
for all the Search Keywords.

To download all the results of your query, use:

.. code-block:: python

    api.download_all()

To get a geojson FeatureCollection containing the footprints and metadata for the search results of the query, use:

.. code-block:: python

    api.get_footprints()

The download from https://scihub.esa.int will fail if the server certificate
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
=======

* Wille Marcel
* Kersten Clauss
* Michele Citterio

License
=======

GPLv3+
