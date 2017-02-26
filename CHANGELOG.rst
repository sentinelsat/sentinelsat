Change Log
==========

All notable changes to ``sentinelsat`` will be listed here.

[0.9]
-----

Added
~~~~~

-  Added ``to_dict``, ``to_dataframe`` and ``to_geodataframe`` which convert the
response content to respective types. The pandas, geopandas and shapely dependencies
are not installed by default.

Changed
~~~~~~~

-  ``--footprints`` now includes all returned product properties in the output.
-  ``KeyError('No results returned.')`` is no longer returned for zero returned products in a response.
-  Renamed ``get_footprint`` to ``to_geojson`` and ``get_product_info`` to ``get_product_odata``.
-  Added underscore to methods and functions that are not expected to be used outside the package.
-  Instance variables ``url`` and ``content`` have been removed,
``last_query`` and ``last_status_code`` have been made private.

[0.8.1] - 2017-02-05
--------------------

Added
~~~~~

-  added a changelog

Changed
~~~~~~~

-  use logging instead of print

Fixed
~~~~~

-  docs represent new ``query`` and ``download_all`` behaviour

[0.8] - 2017-01-27
------------------

Added
~~~~~

-  options to create new, reset or ignore vcr cassettes for testing

Changed
~~~~~~~

-  ``query`` now returns a list of search results
-  ``download_all`` requires the list of search results as an argument

Removed
~~~~~~~

-  ``SentinelAPI`` does not save query results as class attributes

[0.7.4] - 2017-01-14
--------------------

Added
~~~~~

-  Travis tests for Python 3.6

[0.7.3] - 2016-12-09
--------------------

Changed
~~~~~~~

-  changed ``SentinelAPI`` ``max_rows`` attribute to ``page_size`` to
   better reflect pagination
-  tests use ``vcrpy`` cassettes

Fixed
~~~~~

-  support GeoJSON polygons with optional (third) z-coordinate

[0.7.1] - 2016-10-28
--------------------

Added
~~~~~

-  pagination support for query results

Changed
~~~~~~~

-  number of query results per page set to 100

[0.6.5] - 2016-06-22
--------------------

Added
-----

-  support for large queries

Changed
~~~~~~~

-  removed redundant information from Readme that is also present on
   Readthedocs

[0.6.4] - 2016-04-06-03
-----------------------

Changed
~~~~~~~

-  ``initial_date`` / ``--start`` changed from ingestion to acquisition
   date

[0.6.1] - 2016-04-22
--------------------

Added
~~~~~

-  Sphinx documentation setup with autodoc and numpydoc
-  Redthedocs.org integration

[0.5.5] - 2016-01-13
--------------------

Added
~~~~~

-  Sentinel-2 support

[0.5.1] - 2015-12-18
--------------------

Added
~~~~~

-  Travis added as continuous integration service for automated testing

[0.5] - 2015-12-09
------------------

Added
~~~~~

-  validate downloaded products with their MD5 checksums

[0.4.3] - 2015-11-23
--------------------

Added
~~~~~

-  option to select a different dhus api ``--url``

Changed
~~~~~~~

-  ``https://scihub.esa.int/apihub/`` as standard url

[0.4] - 2015-09-28
------------------

Added
~~~~~

-  method to manually select the CA certificate bundle
-  function to return footprints of the queried Sentinel scenes

Fixed
~~~~~

-  CA-certificate SSL errors

[0.3] - 2015-06-10
------------------

Added
~~~~~

-  ``--query`` parameter to use extra search keywords in the cli

[0.1] - 2015-06-05
------------------
