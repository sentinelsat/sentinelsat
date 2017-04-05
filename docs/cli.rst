.. _cli:

Command Line Interface
======================

Sentinelsat's CLI is divided into two commands:

- ``sentinel search`` to query and download a number of images over an area
- ``sentinel download`` to download individual images by their unique identifier

Quickstart
----------

A basic search query consists of a search polygon as well as the username and
password to access the Scihub.

.. code-block:: bash

  sentinel search [OPTIONS] <user> <password> <geojson>

Search areas are provided as GeoJSON polygons, which can be created with
`QGIS <http://qgis.org/en/site/>`_ or `geojson.io <http://geojson.io>`_.
If you do not specify a start and end date only products published in the last
24 hours will be queried.

Start and end dates refer to the acquisition date given by the
`beginPosition <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ of the
products, i.e. the start of the acquisition time.

Sentinel-1
~~~~~~~~~~

Search and download all Sentinel-1 scenes of type SLC, in descending
orbit for the year 2015.

.. code-block:: bash

  sentinel search -s 20150101 -e 20151231 -d \
  -q "producttype=SLC, orbitdirection=Descending" \
  -u "https://scihub.copernicus.eu/dhus" <user> <password> <poly.geojson>

Download a single Sentinel-1 GRDH scene covering Santa Claus Village in Finland
on Christmas Eve 2015.

.. code-block:: bash

  sentinel download --md5 -u "https://scihub.copernicus.eu/dhus/" <user> <password> a9048d1d-fea6-4df8-bedd-7bcb212be12e


Sentinel-2
~~~~~~~~~~

Search and download Sentinel-2 scenes for January 2016 with a maximum cloud
cover of 40%.

.. code-block:: bash

  sentinel search -s 20160101 -e 20160131 --sentinel2 --cloud 40 <user> <password> <poly.geojson>

Download all Sentinel-2 scenes published in the last 24 hours.

.. code-block:: bash

  sentinel search --sentinel2 <user> <password> <poly.geojson>

sentinel search
---------------

.. code-block:: console

    sentinel search [OPTIONS] <user> <password> <geojson>

Options:

+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-s` | :option:`--start`     | TEXT | Start date of the query in the format YYYYMMDD.                                            |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-e` | :option:`--end`       | TEXT | End date of the query in the format YYYYMMDD.                                              |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-d` | :option:`--download`  |      | Download all results of the query.                                                         |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-f` | :option:`--footprints`|      | Create geojson file search_footprints.geojson with footprints of the query result.         |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-p` | :option:`--path`      | PATH | Set the path where the files will be saved.                                                |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-q` | :option:`--query`     | TEXT | Extra search keywords you want to use in the query. Separate keywords with comma.          |
|              |                       |      | Example: 'producttype=GRD,polarisationmode=HH'.                                            |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-u` | :option:`--url`       | TEXT | Define another API URL. Default URL is 'https://scihub.copernicus.eu/apihub/'.             |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--md5`       |      | Verify the MD5 checksum and write corrupt product ids and filenames to corrupt_scenes.txt. |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--sentinel1` |      | Limit search to Sentinel-1 products.                                                       |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--sentinel2` |      | Limit search to Sentinel-2 products.                                                       |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-c` | :option:`--cloud`     | INT  | Maximum cloud cover in percent. (Automatically sets --sentinel2)                           |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--help`      |      | Show help message and exit.                                                                |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--version`   |      | Show version number and exit.                                                              |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+

Query parameters:

ESA maintains a `list of valid search keywords
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ to query the SciHub.

sentinel download
-----------------

.. code-block:: console

    sentinel download [OPTIONS] <user> <password> <productid>

Options:

+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-p` | :option:`--path`      | PATH | Set the path where the files will be saved.                                                |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
| :option:`-u` | :option:`--url`       | TEXT | Define another API URL. Default URL is 'https://scihub.copernicus.eu/apihub/'.             |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--md5`       |      | Verify the MD5 checksum and write corrupt product ids and filenames to corrupt_scenes.txt. |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
|              | :option:`--version`   |      | Show version number and exit.                                                              |
+--------------+-----------------------+------+--------------------------------------------------------------------------------------------+
