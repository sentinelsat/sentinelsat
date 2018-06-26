Change Log
==========

All notable changes to ``sentinelsat`` will be listed here.

[master] – YYYY-MM-DD
---------------------

Added
~~~~~
* Query keywords with interval ranges now support single-sided ranges by using ``None`` or ``'*'`` to note no bounds,
  for example ``query(date=(None, 'NOW-1YEAR'))``. In case both bounds are set to unlimited, the keyword will be removed
  from the query. (#210)
* Raise an exception in case of duplicate keywords present in a query, taking into account the fact that query keywords
  are allowed to be case-insensitive on the server side. (#210)

Changed
~~~~~~~
* Replaced ``[test]`` and ``[docs]`` with a single ``[dev]`` installation extras target. Removed 'requirements.txt'. (#208)

Deprecated
~~~~~~~~~~
* 

Fixed
~~~~~
* Fixed some CLI errors not returning with a non-zero exit code. (#209)

[0.12.2] – 2018-06-20
---------------------

Added
~~~~~
* made exceptions more verbose regarding optional dependencies (#176)
* CLI username, password and DHuS URL can be set with environment variables ``DHUS_USER``, ``DHUS_PASSWORD`` and ``DHUS_URL`` (#184, @temal-)
* added information about known errors and DHuS issues to docs (#186, @martinber)

Changed
~~~~~~~
* remove hard coded product type list from cli (#190, @lenniezelk)
* Made the function signature of ``count()`` fully compatible with ``query()``. Irrelevant parameters are simply ignored.

Deprecated
~~~~~~~~~~
* environment variables ``SENTINEL_USER`` and ``SENTINEL_PASSWORD`` are superceded by ``DHUS_USER`` and ``DHUS_PASSWORD``

Fixed
~~~~~
* Updated handling of invalid queries. An exception is raised in such cases. #168
* Fixed ``order_by`` parameter being ignored in queries that require multiple subqueries (that is, queries that return
  more than 100 products) (#200)
* Special handling of quote symbols in query strings due to a server-side error is no
  longer necessary and has been removed. #168
* Updated effective query length calculation in ``check_query_length()`` to reflect
  server-side changes.
* skip failing tests on optional dependency Pandas for Python 3.3 and 3.4
* Unit tests work irrespective of the directory they are run from.

[0.12.1] – 2017-10-24
---------------------

Changed
~~~~~~~
* Made checksumming the default behavior, and removed its flag from the CLI. (@gbaier2)

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
* Show the correct progress value in the download progressbar when continuing from an incomplete file. (Thanks @gbaier!)
* Added a workaround for a server-side bug when plus symbols are used in a query.


[0.11] – 2017-06-01
-------------------

Changed
~~~~~~~
* Replace ``pycurl`` dependency with ``requests``. This makes installation significantly easier. (#117)
* An exception is raised in ``download_all()`` if all downloads failed.
* Change 'Sentinels Scientific Datahub' to 'Copernicus Open Access Hub' (#100)
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
    (Issue #101)
  - Date arguments can be disabled by setting them to ``None`` and their values are
    validated on the client side. (Issue #101)
  - The return value has been changed to a dict of dicts of parsed metadata values. One entry per
    product with the product ID as the key.

* ``download_all()`` expects a list of product IDs as input. This is compatible with the output of
  ``query()``.
* ``get_coordinates()`` has been replaced with functions ``read_geojson()`` and
  ``geojson_to_wkt()``. (Issue #101)
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
* Fixed invalid GeoJSON output in both the CLI and API. (Issue #104)
* Fixed broken reporting of failed downloads in the CLI. (Issue #88)
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
