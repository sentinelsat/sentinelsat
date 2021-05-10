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

  machine apihub.copernicus.eu
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
  --url "https://apihub.copernicus.eu/apihub"

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

Options
-------

.. program:: sentinelsat

.. option:: -u <username>, --user <username>

    Username. Required.

    Can also be set via the :envvar:`DHUS_USER` environment variable or with a `.netrc file <#quickstart>`_.

.. option:: -p <password>, --password <password>

    Password. Required.

    Can also be set with the :envvar:`DHUS_PASSWORD` environment variable or with a `.netrc file <#quickstart>`_.

.. option:: --url <api_url>

    Define another API URL. Default is 'https://apihub.copernicus.eu/apihub/'.

    Can also be set with the :envvar:`DHUS_URL` environment variable.

.. option:: -s <date>, --start <date>

    Start date of the query in the format YYYYMMDD or one of the other formats listed `here <api_reference.html#sentinelsat.sentinel.SentinelAPI.query>`_.

.. option:: -e <date>, --end <date>

    End date of the query in the format YYYYMMDD or one of the other formats listed `here <api_reference.html#sentinelsat.sentinel.SentinelAPI.query>`_.

.. option:: -g <file>, --geometry <file>

    Search area geometry as GeoJSON file.

.. option:: --uuid

    Select a specific product UUID. Can be used more than once.

.. option:: --name <name>

    Select specific product(s) by filename. Supports wildcards, such as ``S1A_IW*20151224*`` to find all Sentinel-1A
    scenes from 24th of December 2015 without restricting the result to a search area. Can be set more than once.

.. option:: --sentinel <number>

    Limit search to a Sentinel satellite (constellation).

.. option:: --instrument <instrument name>

    Limit search to a specific instrument on a Sentinel satellite.

.. option:: --producttype <product type>

    Limit search to a Sentinel product type.
    List of valid product types can be found under `producttype` `here <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.

.. option:: -c <percent>, --cloud <percent>

    Maximum cloud cover in percent. (requires :option:`--sentinel` to be 2 or 3)

.. option:: -o <keywords>, --order-by <keywords>

    Comma-separated list of keywords to order the result by. Prefix with '-' for descending order.

.. option:: -l <number>, --limit <number>

    Maximum number of results to return. Defaults to no limit.

.. option:: -d, --download

    Download all results of the query.

.. option:: --path <directory>

    Set the directory where the files will be saved.

.. option:: -q <query>, --query <query>

    Extra search keywords you want to use in the query. Repeated keywords get interpreted as an "or" expression.

    ESA maintains a `list of valid search keywords <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ that can be used.

    Example: `-q producttype=GRD -q polarisationmode=HH`.

.. option:: -f, --footprints <path>

    Create a GeoJSON file at the provided path with footprints
    and metadata of the returned products. Set to '-' for stdout.

.. option:: --include-pattern

    Glob pattern to filter files (within each product) to be downloaded.

.. option:: --exclude-pattern

    Glob pattern to filter files (within each product) to be excluded
    from the downloaded.

.. option:: --info

    Display DHuS server information.

.. option:: --version

    Show version number and exit.

.. option:: --debug

    Print debug log messages.

.. option:: -h, --help

    Show help message and exit.


The options :option:`--sentinel`, :option:`--instrument` and :option:`--producttype` are mutually exclusive and follow a hierarchy from
most specific to least specific, i.e. :option:`--producttype` > :option:`--instrument` > :option:`--sentinel`. Only the most specific
option will be included in the search when multiple ones are given.

Also the :option:`--include-pattern` and :option:`--exclude-patter` options are mutually exclusive.
If used together the CLI program exists with an error.
