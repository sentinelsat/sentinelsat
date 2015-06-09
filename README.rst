sentinelsat
============

.. image:: https://badge.fury.io/py/sentinelsat.svg
    :target: http://badge.fury.io/py/sentinelsat


Utility pack to search and download Sentinel-1 imagery.

Installation
============

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
Beyond your scihub user and password, you must pass a geojson file
containing the polygon of the area that you want to search for. If you
don't especify the start and end dates, it will search in the last 24
hours.

Options:

-s, --start TEXT  Start date of the query in the format YYYYMMDD.
-e, --end TEXT    End date of the query in the format YYYYMMDD.
-d, --download    Download all results of the query.
-p, --path PATH   Set the path where the files will be saved.

Download
^^^^^^^^

.. code-block:: console

    sentinel download [OPTIONS] <user> <password> <productid>

Download a Sentinel-1 Product. It just needs your scihub user and password and
the id of the product you want to download.

Options:

-p, --path PATH  Set the path where the file will be saved.


Python Library
--------------

Connect to the API:

.. code-block:: python

    from sentinelsat.sentinel import SentinelAPI
    api = SentinelAPI('user', 'password')

If you know the id of the product you want to download, you can download it by using:

.. code-block:: python

    api.download(<product_id>)

You can search products by specifying the coordinates of the area and a date interval:

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', '20150531', '20150612')

You can query by using date or datetime objects too.

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', datetime(2015, 5, 31, 12, 5), date(2015, 6, 12))

If you don't specify the start and end dates, it will query in the last 24 hours.

Beyond area and date parameters, you can use any search keywords accepted by the SciHub API, for example:

.. code-block:: python

    api.query('0 0,1 1,0 1,0 0', producttype='SLC')

See the `SciHub User Guide <https://scihub.esa.int/twiki/do/view/SciHubUserGuide/FullTextSearch#Search_Keywords>`_
for all the Search Keywords.

To download all the results of your query, use:

.. code-block:: python

    api.download_all()

License
=======

GPLv3+
