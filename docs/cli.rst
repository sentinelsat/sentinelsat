.. _cli:

Command Line Interface
======================

Sentinelsat provides a CLI :program:`sentinelsat` to query and download multiple or single images.

Quickstart
----------

A basic search query consists of a search polygon as well as the username and
password to access the Copernicus Open Access Hub.

.. code-block:: bash

  sentinelsat -u <user> -p <password> -g <search_polygon.geojson>

For convenience and added security, there are two ways you can store your credentials and omit them from the command line call. 
You can set username, password and DHuS URL as environment variables.

.. code-block:: bash

  export DHUS_USER="<user>"
  export DHUS_PASSWORD="<password>"
  export DHUS_URL="<api_url>"

Alternatively, you can add them to a file `.netrc` in your user home directory.

.. code-block:: text

  machine scihub.copernicus.eu
  login <user>
  password <password>

Environment variables take precedence over `.netrc`. The above command then becomes

.. code-block:: bash

  sentinelsat -g <search_polygon.geojson>

Search areas (i.e. ``search_polygon.geojson`` ) are provided as GeoJSON files, which can be created with
`QGIS <http://qgis.org/en/site/>`_ or `geojson.io <http://geojson.io>`_.
If you do not specify a start and end date only products published in the last
24 hours will be queried.

Start and end dates refer to the acquisition date given by the
`beginPosition <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ of the
products, i.e. the start of the acquisition time.

Sentinel-1
~~~~~~~~~~

Search and download all Sentinel-1 scenes of type SLC over a search polygon, in descending
orbit for the year 2015.

.. code-block:: bash

  sentinelsat -u <user> -p <password> -g <search_polygon.geojson> -s 20150101 -e 20151231 -d \
  --producttype SLC -q "orbitdirection=Descending" \
  --url "https://scihub.copernicus.eu/dhus"

Download a single Sentinel-1 GRDH scene covering Santa Claus Village in Finland
on Christmas Eve 2015.

.. code-block:: bash

  sentinelsat -u <user> -p <password> -d --uuid a9048d1d-fea6-4df8-bedd-7bcb212be12e

or by using its filename

.. code-block:: bash

  sentinelsat -u <user> -p <password> -d --name S1A_EW_GRDM_1SDH_20151224T154142_20151224T154207_009186_00D3B0_C71E

Sentinel-2
~~~~~~~~~~

Search and download Sentinel-2 scenes for January 2016 with a maximum cloud
cover of 40%.

.. code-block:: bash

  sentinelsat -u <user> -p <password> -g <search_polygon.geojson> -s 20160101 -e 20160131 --sentinel 2 --cloud 40 -d

Download all Sentinel-2 scenes published in the last 24 hours.

.. code-block:: bash

  sentinelsat -u <user> -p <password> -g <search_polygon.geojson> --sentinel 2 -d

sentinelsat
---------------

.. program:: sentinelsat

.. code-block:: console

    sentinelsat -u <user> -p <password> [OPTIONS]

Options:

+----+---------------+------+--------------------------------------------------------------------------------------------+
| -u | -\-user       | TEXT | Username [required] (or environment variable :envvar:`DHUS_USER`)                          |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -p | -\-password   | TEXT | Password [required] (or environment variable :envvar:`DHUS_PASSWORD`)                      |
+----+---------------+------+--------------------------------------------------------------------------------------------+
|    | -\-url        | TEXT | Define another API URL. Default URL is 'https://scihub.copernicus.eu/dhus/'.             |
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
|    | -\-producttype| TEXT | Limit search to a Sentinel product type. List of valid product types can be found under    |
|    |               |      | `producttype` `here <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.            |
+----+---------------+------+--------------------------------------------------------------------------------------------+
| -c | -\-cloud      | INT  | Maximum cloud cover in percent. (requires :option:`--sentinel` to be 2 or 3)               |
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

ESA maintains a `list of valid search keywords <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ that can be used with :option:`--query`.

The options :option:`--sentinel`, :option:`--instrument` and :option:`--producttype` are mutually exclusive and follow a hierarchy from
most specific to least specific, i.e. :option:`--producttype` > :option:`--instrument` > :option:`--sentinel`. Only the most specific
option will be included in the search when multiple ones are given.

Searching by name supports wildcards, such as ``S1A_IW*20151224*`` to find all Sentinel-1 A scenes from 24th of December 2015 without
restricting the result to a search area.
