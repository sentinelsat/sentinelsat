Change Log
==========

All notable changes to ``sentinelsat`` will be listed here.

[0.11.1] – 2017-XX-XX
---------------------

Added
~~~~~
* contribution guidelines


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
