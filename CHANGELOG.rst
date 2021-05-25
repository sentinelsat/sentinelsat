Change Log
==========

All notable changes to ``sentinelsat`` will be listed here.

[Unreleased] – YYYY-MM-DD
-------------------------

CLI changes
~~~~~~~~~~~
* 

Added
~~~~~
* 

Changed
~~~~~~~
* 

Fixed
~~~~~
* 


[1.0.1] – 2021-05-25
-------------------------

Fixed
~~~~~
* Fixed broken triggering of offline LTA products - use GET instead of HEAD since HEAD does not appear to be triggering retrieval correctly. (`#486 <https://github.com/sentinelsat/sentinelsat/issues/486>`_ `@valgur <https://github.com/valgur>`_, related to `#386 <https://github.com/sentinelsat/sentinelsat/issues/386>`_)


[1.0.0] – 2021-05-19
---------------------
* Dropped support for Python 2.7. Now setuptools requires Python >= 3.6.

CLI changes
~~~~~~~~~~~
* ``--start`` and ``--end`` CLI arguments no longer use the default values of ``NOW-1DAY`` and ``NOW``. (`#459 <https://github.com/sentinelsat/sentinelsat/issues/459>`_ `@valgur <https://github.com/valgur>`_)
* ``--footprints`` now expects a path for the output file to be specified instead of using the previous default ``<--path>/search_footprints.geojson``. (`#462 <https://github.com/sentinelsat/sentinelsat/issues/462>`_ `@valgur <https://github.com/valgur>`_, `#407 <https://github.com/sentinelsat/sentinelsat/issues/407>`_ `@IpsumCapra <https://github.com/IpsumCapra>`_)
* ``--uuid``, ``--name`` and ``--query`` must now be repeated instead of passing a single comma-separated string.
  Repeated keywords get treated as an "or" expression. (`#463 <https://github.com/sentinelsat/sentinelsat/issues/463>`_ `@valgur <https://github.com/valgur>`_)
* Display DHuS server version with CLI flag ``--info`` (`#367 <https://github.com/sentinelsat/sentinelsat/issues/367>`_ `@thomasyoung-audet <https://github.com/thomasyoung-audet>`_)
* Added searching by placenames with the CLI flag ``--location`` (`#372 <https://github.com/sentinelsat/sentinelsat/issues/372>`_ `@thomasyoung-audet <https://github.com/thomasyoung-audet>`_)
* Added CLI support for ``--geometry`` input as a WKT or GeoJSON string (`#381 <https://github.com/sentinelsat/sentinelsat/issues/381>`_ `@thomasyoung-audet <https://github.com/thomasyoung-audet>`_)
* Download quicklooks directly with the CLI flag ``--quicklook`` (`#361 <https://github.com/sentinelsat/sentinelsat/issues/361>`_ `@mackland <https://github.com/mackland>`_)
* Got rid of the special handling of ``--uuid`` and ``--name`` CLI arguments. The product IDs are now simply passed to ``api.query()`` as a set.
  As a result they no longer ignore the date range arguments (fixes `#387 <https://github.com/sentinelsat/sentinelsat/issues/387>`_). (`#390 <https://github.com/sentinelsat/sentinelsat/issues/390>`_ `@valgur <https://github.com/valgur>`_)
* Added ``--timeout`` option with a default value of 60 seconds to avoid waiting indefinitely for a response. (`#475 <https://github.com/sentinelsat/sentinelsat/issues/475>`_ `@valgur <https://github.com/valgur>`_)
* New ``--gnss`` CLI flag to use the GNSS end-point for orbit products query and download (`#441 <https://github.com/sentinelsat/sentinelsat/issues/441>`_ `@avalentino <https://github.com/avalentino>`_).

Added
~~~~~
* Added ``setinelsat/__main__.py`` (`#412 <https://github.com/sentinelsat/sentinelsat/issues/412>`_ `@avalentino <https://github.com/avalentino>`_)
* Added ``get_stream()`` (`#430 <https://github.com/sentinelsat/sentinelsat/issues/430>`_ `@fwfichtner <https://github.com/fwfichtner>`_)
* New ``sentinelsat/products.py`` module providing a "product nodes" API that
  allows to filter and download only selected files of the requested products
  (`#414 <https://github.com/sentinelsat/sentinelsat/issues/414>`_ `@avalentino <https://github.com/avalentino>`_)
* Added ``trigger_offline_retrieval()``. (`#476 <https://github.com/sentinelsat/sentinelsat/issues/476>`_ `@valgur <https://github.com/valgur>`_)
* Added ``download_quicklooks()`` and ``download_all_quicklooks()`` (`#361 <https://github.com/sentinelsat/sentinelsat/issues/361>`_ `@mackland <https://github.com/mackland>`_)

Changed
~~~~~~~
* Replaced ``SentinelAPIError`` exceptions with more specific types:

  * ``SentinelAPIError`` -- the parent, catch-all exception. Only used when no other more specific exception can be applied.
  * ``ServerError`` -- raised when the server responded in an unexpected manner, typically due to undergoing maintenance.
  * ``UnauthorizedError`` -- raised when attempting to retrieve a product with incorrect credentials.
  * ``QuerySyntaxError`` -- raised when the query string could not be parsed on the server side.
  * ``QueryLengthError`` -- raised when the query string length was excessively long.
  * ``InvalidKeyError`` -- raised when product with given key was not found on the server.
  * ``InvalidChecksumError`` -- MD5 checksum of a local file does not match the one from the server.
  * ``LTAError`` -- raised when triggering a retrieval from the Long Term Archive failed.
  * ``LTATriggered`` -- raised in some cases when the product is offline and retrieval was triggered successfully.

  The new exceptions are still subclasses of ``SentinelAPIError`` for backwards compatibility.
  (`#285 <https://github.com/sentinelsat/sentinelsat/issues/285>`_ `@valgur <https://github.com/valgur>`_, `@dwlsalmeida <https://github.com/dwlsalmeida>`_)
* Tidied up the (internal) download code logic (`#378 <https://github.com/sentinelsat/sentinelsat/issues/378>`_ `@valgur <https://github.com/valgur>`_)
* Added an "exception" field to the ``failed_products`` dict returned by in ``.download_all()`` for easier debugging (`#378 <https://github.com/sentinelsat/sentinelsat/issues/378>`_ `@valgur <https://github.com/valgur>`_)
* Fixed the server-side space handling change issue reported in `#383 <https://github.com/sentinelsat/sentinelsat/issues/383>`_ by quoting instead of backslash-escaping the strings. (`#390 <https://github.com/sentinelsat/sentinelsat/issues/390>`_ `@valgur <https://github.com/valgur>`_)
* Queries now use ``(key:value OR key:value)`` format instead of the previous ``key:(value OR value)`` format,
  which for some reason took tens of seconds per query. (`#390 <https://github.com/sentinelsat/sentinelsat/issues/390>`_ `@valgur <https://github.com/valgur>`_)
* Empty queries raise a ``ValueError`` immediately on the client side instead of letting the server generate it. (`#390 <https://github.com/sentinelsat/sentinelsat/issues/390>`_ `@valgur <https://github.com/valgur>`_)
* Added stricter checks for empty keyword values in queries, which would cause server-side errors. (`#390 <https://github.com/sentinelsat/sentinelsat/issues/390>`_ `@valgur <https://github.com/valgur>`_)
* Gracefully handle cancelled futures. (`#448 <https://github.com/sentinelsat/sentinelsat/issues/448>`_ and `#479 <https://github.com/sentinelsat/sentinelsat/issues/479>`_ `@avalentino <https://github.com/avalentino>`_)
* Use the HTTP status instead of OData metadata to determine the online status of a product when downloading. 
  This is a workaround for the rare server-side bug of the OData info for the online status being incorrect (`#467 <https://github.com/sentinelsat/sentinelsat/issues/467>`_). (`#469 <https://github.com/sentinelsat/sentinelsat/issues/469>`_ `@valgur <https://github.com/valgur>`_)
* ``download()`` now raises ``LTATriggered`` or ``LTAError`` if the requested product is offline. (`#476 <https://github.com/sentinelsat/sentinelsat/issues/476>`_ `@valgur <https://github.com/valgur>`_)
  This is a workaround for the rare server-side bug of the OData info for the online status being incorrect (`#467 <https://github.com/sentinelsat/sentinelsat/issues/467>`_). (`#469 <https://github.com/sentinelsat/sentinelsat/issues/469>`_ `@valgur <https://github.com/valgur>`_) 
* Set the default query timeout to 60 seconds to avoid waiting indefinitely for a response. (`#475 <https://github.com/sentinelsat/sentinelsat/issues/475>`_ `@valgur <https://github.com/valgur>`_)
* ``download_all`` now returns a named tuple for clarity. (`#477 <https://github.com/sentinelsat/sentinelsat/issues/477>`_ `@valgur <https://github.com/valgur>`_)
* Search queries now use GET instead of POST requests because the Sentinel-5P Pre-Operations Data Hub does not support POST (`#380 <https://github.com/sentinelsat/sentinelsat/issues/380>`_).
  As a consequence, the search query contents are now limited to latin1 encoding instead of UTF-8. (`#473 <https://github.com/sentinelsat/sentinelsat/issues/473>`_ `@valgur <https://github.com/valgur>`_)
* Use ``tqdm.auto`` for nicer progress reporting in notebooks. (`#480 <https://github.com/sentinelsat/sentinelsat/issues/480>`_ `@valgur <https://github.com/valgur>`_)

Deprecated
~~~~~~~~~~
* Removed ``query_raw()`` that was deprecated in v0.12.

Fixed
~~~~~
* Fix location information for Nominatim bounding box queries (`#384 <https://github.com/sentinelsat/sentinelsat/issues/384>`_)
* Get file name extension more reliably from either the HTTP header or an OData attribute. (`#378 <https://github.com/sentinelsat/sentinelsat/issues/378>`_, `#472 <https://github.com/sentinelsat/sentinelsat/issues/472>`_ `@valgur <https://github.com/valgur>`_)
* Updated the API Hub URL to `https://apihub.copernicus.eu/apihub/`.
* Server-side error info has become much more detailed and the client code has been updated to correctly handle that.
* ``check_existing()`` now determines the filename correctly for Sentinel-5 products. (`@valgur <https://github.com/valgur>`_ `#452 <https://github.com/sentinelsat/sentinelsat/issues/452>`_)
* Fix accidental downloading of the whole product in memory when the product is actually available despite being marked
  as offline in its metadata. (`#386 <https://github.com/sentinelsat/sentinelsat/issues/386>`_, `#421 <https://github.com/sentinelsat/sentinelsat/issues/421>`_, `#454 <https://github.com/sentinelsat/sentinelsat/issues/454>`_ `@lucadelu <https://github.com/lucadelu>`_)
* Fixed timeout not being used in some queries. (`#454 <https://github.com/sentinelsat/sentinelsat/issues/454>`_ `@valgur <https://github.com/valgur>`_)

Development Changes
~~~~~~~~~~~~~~~~~~~
* Fixed failing Read The Docs builds (`#370 <https://github.com/sentinelsat/sentinelsat/issues/370>`_)
* Replaced Travis CI with Github Actions. Added testing on MacOS and Windows. (`#438 <https://github.com/sentinelsat/sentinelsat/issues/438>`_ `@avalentino <https://github.com/avalentino>`_)
* Made tests more robust by not relying on specific products being returned where possible.


[0.14] – 2020-06-12
---------------------

Added
~~~~~
* trigger retrieval of offline products from LTA, while downloading online products (`#297 <https://github.com/sentinelsat/sentinelsat/issues/297>`_ `@gbaier <https://github.com/gbaier>`_)
* allow input of multiple values per query parameter as logical OR (`#321 <https://github.com/sentinelsat/sentinelsat/issues/321>`_ `@OlgaCh <https://github.com/OlgaCh>`_)
* document CODA password limitations (`#315 <https://github.com/sentinelsat/sentinelsat/issues/315>`_ `@nishadhka <https://github.com/nishadhka>`_)

Changed
~~~~~~~
* warn users about complex queries (`#290 <https://github.com/sentinelsat/sentinelsat/issues/290>`_)

Deprecated
~~~~~~~~~~
* discontinued support for Python <=3.4

Fixed
~~~~~
* Missing ``Online`` field in OData response defaults to ``Online: True`` instead of raising a ``KeyError`` (`#281 <https://github.com/sentinelsat/sentinelsat/issues/281>`_ `@viktorbahr <https://github.com/viktorbahr>`_)
* Missing ``ContentGeometry`` field in OData response defaults to ``footprint: None`` instead of raising a ``TypeError`` (`#286 <https://github.com/sentinelsat/sentinelsat/issues/286>`_ `#325 <https://github.com/sentinelsat/sentinelsat/issues/325>`_ `@lukasbindreiter <https://github.com/lukasbindreiter>`_)

Development Changes
~~~~~~~~~~~~~~~~~~~
* code formatting with `black` checked by Travis-CI (`#352 <https://github.com/sentinelsat/sentinelsat/issues/352>`_)
* reorganize unit tests into small groups with their own files (`#287 <https://github.com/sentinelsat/sentinelsat/issues/287>`_)
* reduced code duplication in unit tests by making greater use of pytest fixtures. (`#287 <https://github.com/sentinelsat/sentinelsat/issues/287>`_)
* force unit tests to include one of the markers 'fast', 'scihub' or 'mock_api' (`#287 <https://github.com/sentinelsat/sentinelsat/issues/287>`_)
* automatic return code checking of CLI tests (`#287 <https://github.com/sentinelsat/sentinelsat/issues/287>`_)
* Replaced direct ``vcrpy`` usage in unit tests with ``pytest-vcr``.
  The ``pytest`` command line options changed from ``--vcr disable`` to ``--disable-vcr`` and
  ``--vcr [use|record_new|reset]`` to ``--vcr-record [once|record_new|all``.
  See `vcrpy docs <https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes>`_ for details. (`#283 <https://github.com/sentinelsat/sentinelsat/issues/283>`_)


[0.13] – 2019-04-05
---------------------

Added
~~~~~
* Query keywords with interval ranges now also support single-sided ranges by using ``None`` or ``'*'`` to denote no bound,
  for example ``query(date=(None, 'NOW-1YEAR'))``. If both bounds are set to unlimited, the keyword will be removed
  from the query. (`#210 <https://github.com/sentinelsat/sentinelsat/issues/210>`_)
* Raise an exception in case of duplicate keywords present in a query. Case is ignored to match the server-side behavior. (`#210 <https://github.com/sentinelsat/sentinelsat/issues/210>`_)
* Support for Python 3.7
* Support for GeoJSON files with a single ``Feature`` without a ``FeatureCollection.`` (`#224 <https://github.com/sentinelsat/sentinelsat/issues/224>`_ `@scottstanie <https://github.com/scottstanie>`_)
* Added support for Unicode symbols in search queries. (`#230 <https://github.com/sentinelsat/sentinelsat/issues/230>`_)
* Raise ValueError exception if longitude is outside [-180, 180] or latitude is outside [-90, 90] (`#236 <https://github.com/sentinelsat/sentinelsat/issues/236>`_, `#218 <https://github.com/sentinelsat/sentinelsat/issues/218>`_ `@Andrey-Raspopov <https://github.com/Andrey-Raspopov>`_)
* optional ``timeout`` attribute to avoid indefinite wait on response from the server (`#256 <https://github.com/sentinelsat/sentinelsat/issues/256>`_, `@viktorbahr <https://github.com/viktorbahr>`_)
* Parsing the ``Online``, ``CreationDate`` and ``IngestionDate`` fields of an OData response
* Trying to download an offline product from the Copernicus Open Access Hub triggers its retrieval from the long term archive.
  Downloading of the product is **not** scheduled.
* Added support for downloading Sentinel 5P data in the CLI via the '--sentinel 5' flag

Changed
~~~~~~~
* Add support in the CLI for reading credentials from `~/.netrc` and document existing functionality in the API (`#90 <https://github.com/sentinelsat/sentinelsat/issues/90>`_)

Fixed
~~~~~
* Spaces in query parameter values are now handled correctly be escaping them with a backslash, where appropriate. (`#169 <https://github.com/sentinelsat/sentinelsat/issues/169>`_, `#211 <https://github.com/sentinelsat/sentinelsat/issues/211>`_)
* Fixed some CLI errors not returning a non-zero exit code. (`#209 <https://github.com/sentinelsat/sentinelsat/issues/209>`_)
* Fixed typo for ``area_relation`` query parameter documentation from ``'Intersection'`` to ``'Intersects'``. (`#225 <https://github.com/sentinelsat/sentinelsat/issues/225>`_ `@scottstanie <https://github.com/scottstanie>`_)
* Updated ``check_query_length()`` logic to match the changed server-side behavior. (`#230 <https://github.com/sentinelsat/sentinelsat/issues/230>`_)
* Clarify usage of GeoJSON files with CLI in docs (`#229 <https://github.com/sentinelsat/sentinelsat/issues/229>`_ `@psal93 <https://github.com/psal93>`_)
* ``to_geopandas()`` now returns an empty GeoDataFrame for an empty product list input.

Development Changes
~~~~~~~~~~~~~~~~~~~
* Replaced ``[test]`` and ``[docs]`` with a single ``[dev]`` installation extras target. (`#208 <https://github.com/sentinelsat/sentinelsat/issues/208>`_)
* Adapted `.travis.yml` to build `fiona` and `pyproj` from source for Python 3.7.
* Minimum pytest version ``pytest >= 3.6.3`` required by ``pytest-socket``.
* The existing practice of not accessing the network from unit tests, unless running with ``--vcr record_new`` or
  ``--vcr reset``, is now enforced by throwing a ``SocketBlockedError`` in such cases. (`#207 <https://github.com/sentinelsat/sentinelsat/issues/207>`_)

[0.12.2] – 2018-06-20
---------------------

Added
~~~~~
* made exceptions more verbose regarding optional dependencies (`#176 <https://github.com/sentinelsat/sentinelsat/issues/176>`_)
* CLI username, password and DHuS URL can be set with environment variables ``DHUS_USER``, ``DHUS_PASSWORD`` and ``DHUS_URL`` (`#184 <https://github.com/sentinelsat/sentinelsat/issues/184>`_, `@temal- <https://github.com/temal->`_)
* added information about known errors and DHuS issues to docs (`#186 <https://github.com/sentinelsat/sentinelsat/issues/186>`_, `@martinber <https://github.com/martinber>`_)

Changed
~~~~~~~
* remove hard coded product type list from cli (`#190 <https://github.com/sentinelsat/sentinelsat/issues/190>`_, `@lenniezelk <https://github.com/lenniezelk>`_)
* Made the function signature of ``count()`` fully compatible with ``query()``. Irrelevant parameters are simply ignored.

Deprecated
~~~~~~~~~~
* environment variables ``SENTINEL_USER`` and ``SENTINEL_PASSWORD`` are superceded by ``DHUS_USER`` and ``DHUS_PASSWORD``

Fixed
~~~~~
* Updated handling of invalid queries. An exception is raised in such cases. `#168 <https://github.com/sentinelsat/sentinelsat/issues/168>`_
* Fixed ``order_by`` parameter being ignored in queries that require multiple subqueries (that is, queries that return
  more than 100 products) (`#200 <https://github.com/sentinelsat/sentinelsat/issues/200>`_)
* Special handling of quote symbols in query strings due to a server-side error is no
  longer necessary and has been removed. `#168 <https://github.com/sentinelsat/sentinelsat/issues/168>`_
* Updated effective query length calculation in ``check_query_length()`` to reflect
  server-side changes.
* skip failing tests on optional dependency Pandas for Python 3.3 and 3.4
* Unit tests work irrespective of the directory they are run from.

[0.12.1] – 2017-10-24
---------------------

Changed
~~~~~~~
* Made checksumming the default behavior, and removed its flag from the CLI. (`@gbaier2 <https://github.com/gbaier2>`_)

Fixed
~~~~~
* set ``requests`` encoding to UTF8
* fixed a backwards incompatible change in the ``geojson`` dependency
* inconsistent documentation on the use of range parameters such as ``date=``


[0.12.0] – 2017-08-10
---------------------

Added
~~~~~
* Option to change the type of spatial relation for the AOI in ``query()``.
  The choices are 'Interesects', 'Contains' and 'IsWithin'.
* ``order_by`` option to ``query()`` which controls the fields by which the products are sorted on the
  server side before being returned. ``-o/--order-by`` on the CLI.
* ``limit`` the number of products returned by ``query()`` and to set the number
  of products to skip via ``offset``. ``-l/--limit`` on the CLI.
* Added ``raw`` parameter to ``query()`` to append any additional raw query string to the query.
* Query parameters that take intervals as values can now be passed a tuple of the interval range values.
* Date validation and parsing has been extended to all date-type parameters in queries, such as 'ingestiondate'.
* Added ``count()`` which quickly returns the number of products matching a query on the server
  without retrieving the full response.
* Method ``check_query_length`` to check if a query will fail because of being excessively long.
* Option to adjust the number of decimal figures in the coordinates of the WKT string returned by ``geojson_to_wkt()``.
* CLI option to query by UUID (``--uuid``) or filename (``--name``).
* A more informative error message is shown if a too long query string was likely the cause
  of the query failing on the server side.
  This can be useful if the WKT string length would cause the query to fail otherwise.
* Progressbars can be disabled by setting ``show_progressbars`` to ``False``.
  Progressbars may be customized by overriding the ``_tqdm()`` method.
* Contribution guidelines.
* Tests for validity of documentation and RST files.

Changed
~~~~~~~
* Merged CLI subcommands ``sentinel search`` and ``sentinel download`` into ``sentinelsat``.
* CLI uses keywords instead of positional arguments, i.e. ``--user <username>``.
* ``initial_date`` and ``end_date`` parameters in ``query()`` have been replaced with a single
  ``date`` parameter that takes a tuple of start and end dates as input.
* Files being downloaded now include an '.incomplete' suffix in their name until the download is finished.
* Removed ``check_existing`` option from ``download()`` and ``download_all()``.
  Similar functionality has been provided in the new ``check_files()`` function.
* ``format_query_date`` has been changed into a public function.
* Added a progressbar to long-running queries.
* Tests can now be run from any directory rather than the repository root.
* Made the query string slightly more compact by getting rid of unnecessary 'AND' operators, spaces and parentheses.
* Reduced the size of the VCR.py cassettes used in unit tests.
* changed license from AGPLv3 to GPLv3+

Deprecated
~~~~~~~~~~
* ``query_raw()`` has been merged with ``query()`` and is deprecated. Use ``query(raw=...)`` instead.

Fixed
~~~~~
* Show the correct progress value in the download progressbar when continuing from an incomplete file. (Thanks `@gbaier <https://github.com/gbaier>`_!)
* Added a workaround for a server-side bug when plus symbols are used in a query.


[0.11] – 2017-06-01
-------------------

Changed
~~~~~~~
* Replace ``pycurl`` dependency with ``requests``. This makes installation significantly easier. (`#117 <https://github.com/sentinelsat/sentinelsat/issues/117>`_)
* An exception is raised in ``download_all()`` if all downloads failed.
* Change 'Sentinels Scientific Datahub' to 'Copernicus Open Access Hub' (`#100 <https://github.com/sentinelsat/sentinelsat/issues/100>`_)
* Renamed ``py.test`` option ``--vcr reset_all`` to ``--vcr reset`` to better reflect its true behavior.


[0.10] – 2017-05-30
-------------------

Added
~~~~~
* GeoJSON footprints are allowed to contain just a single geometry instead of a feature
  collection. Any geometry type that has a WKT equivalent is supported (rather than only
  Polygons).
* ``get_product_odata()`` can be used to get the full metadata information available for a
  product if ``full=True`` is set.
* Added ``query_raw()`` that takes full text search string as input and returns a parsed
  dictionary just like the updated ``query()`` method.
* CLI: ``--sentinel=<int>`` option to select satellite (constellation)

Changed
~~~~~~~
* ``SentinelAPI``, etc. can be directly imported from ``sentinelsat`` rather than
  ``sentinelsat.sentinel``.
* ``query()`` changes:

  - The ``area`` argument expects a WKT string as input instead of a coordinate string.
    (Issue `#101 <https://github.com/sentinelsat/sentinelsat/issues/101>`_)
  - Date arguments can be disabled by setting them to ``None`` and their values are
    validated on the client side. (Issue `#101 <https://github.com/sentinelsat/sentinelsat/issues/101>`_)
  - The return value has been changed to a dict of dicts of parsed metadata values. One entry per
    product with the product ID as the key.

* ``download_all()`` expects a list of product IDs as input. This is compatible with the output of
  ``query()``.
* ``get_coordinates()`` has been replaced with functions ``read_geojson()`` and
  ``geojson_to_wkt()``. (Issue `#101 <https://github.com/sentinelsat/sentinelsat/issues/101>`_)
* Use more compact and descriptive error messages from the response headers, if available.

Deprecated
~~~~~~~~~~
* CLI: ``--sentinel1`` and ``--sentinel2`` will be removed with the next major release

Removed
~~~~~~~
* ``to_dict()`` has been removed since it is no longer required.
* ``load_query()`` has been made private (renamed to ``_load_query()``).


Fixed
~~~~~
* Fixed invalid GeoJSON output in both the CLI and API. (Issue `#104 <https://github.com/sentinelsat/sentinelsat/issues/104>`_)
* Fixed broken reporting of failed downloads in the CLI. (Issue `#88 <https://github.com/sentinelsat/sentinelsat/issues/88>`_)
* Attempting to download a product with an invalid ID no longer creates an infinite loop and a
  more informative error message is displayed in the CLI.


[0.9.1] – 2017-03-06
--------------------

Added
~~~~~
* ``--version`` option to command line utilities
* install requirements for building the documentation
* documentation of sorting with ``to_*`` convenience functions

[0.9] – 2017-02-26
------------------

Added
~~~~~

* Added ``to_dict``, ``to_dataframe`` and ``to_geodataframe`` which convert the
  response content to respective types. The pandas, geopandas and shapely dependencies
  are not installed by default.

Changed
~~~~~~~

* ``--footprints`` now includes all returned product properties in the output.
* ``KeyError('No results returned.')`` is no longer returned for zero returned products in a response.
* Renamed ``get_footprint`` to ``to_geojson`` and ``get_product_info`` to ``get_product_odata``.
* Added underscore to methods and functions that are not expected to be used outside the package.
* Instance variables ``url`` and ``content`` have been removed,
  ``last_query`` and ``last_status_code`` have been made private.

[0.8.1] – 2017-02-05
--------------------

Added
~~~~~

* added a changelog

Changed
~~~~~~~

* use logging instead of print

Fixed
~~~~~

* docs represent new ``query`` and ``download_all`` behaviour

[0.8] – 2017-01-27
------------------

Added
~~~~~

* options to create new, reset or ignore vcr cassettes for testing

Changed
~~~~~~~

* ``query`` now returns a list of search results
* ``download_all`` requires the list of search results as an argument

Removed
~~~~~~~

* ``SentinelAPI`` does not save query results as class attributes

[0.7.4] – 2017-01-14
--------------------

Added
~~~~~

* Travis tests for Python 3.6

[0.7.3] – 2016-12-09
--------------------

Changed
~~~~~~~

* changed ``SentinelAPI`` ``max_rows`` attribute to ``page_size`` to
  better reflect pagination
* tests use ``vcrpy`` cassettes

Fixed
~~~~~

* support GeoJSON polygons with optional (third) z-coordinate

[0.7.1] – 2016-10-28
--------------------

Added
~~~~~

* pagination support for query results

Changed
~~~~~~~

* number of query results per page set to 100

[0.6.5] – 2016-06-22
--------------------

Added
-----

* support for large queries

Changed
~~~~~~~

* Removed redundant information from Readme that is also present on
  Readthedocs

[0.6.4] – 2016-04-06-03
-----------------------

Changed
~~~~~~~

* ``initial_date`` / ``--start`` changed from ingestion to acquisition
  date

[0.6.1] – 2016-04-22
--------------------

Added
~~~~~

* Sphinx documentation setup with autodoc and numpydoc
* Redthedocs.org integration

[0.5.5] – 2016-01-13
--------------------

Added
~~~~~

* Sentinel-2 support

[0.5.1] – 2015-12-18
--------------------

Added
~~~~~

* Travis added as continuous integration service for automated testing

[0.5] – 2015-12-09
------------------

Added
~~~~~

* validate downloaded products with their MD5 checksums

[0.4.3] – 2015-11-23
--------------------

Added
~~~~~

* option to select a different dhus api ``--url``

Changed
~~~~~~~

* ``https://scihub.esa.int/apihub/`` as standard url

[0.4] – 2015-09-28
------------------

Added
~~~~~

* method to manually select the CA certificate bundle
* function to return footprints of the queried Sentinel scenes

Fixed
~~~~~

* CA-certificate SSL errors

[0.3] – 2015-06-10
------------------

Added
~~~~~

* ``--query`` parameter to use extra search keywords in the cli

[0.1] – 2015-06-05
------------------

* first release
