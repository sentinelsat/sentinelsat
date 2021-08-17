.. _api:
.. currentmodule:: sentinelsat

Python API
==========

Quickstart
----------

.. code-block:: python

  # connect to the API
  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
  from datetime import date

  api = SentinelAPI('user', 'password', 'https://apihub.copernicus.eu/apihub')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and SciHub query keywords
  footprint = geojson_to_wkt(read_geojson('/path/to/map.geojson'))
  products = api.query(footprint,
                       date=('20151219', date(2015, 12, 29)),
                       platformname='Sentinel-2',
                       cloudcoverpercentage=(0, 30))

  # download all results from the search
  api.download_all(products)

  # convert to Pandas DataFrame
  products_df = api.to_dataframe(products)

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.to_geojson(products)

  # GeoPandas GeoDataFrame with the metadata of the scenes and the footprints as geometries
  api.to_geodataframe(products)

  # Get basic information about the product: its title, file size, MD5 sum, date, footprint and
  # its download url
  api.get_product_odata(<product_id>)

  # Get the product's full metadata available on the server
  api.get_product_odata(<product_id>, full=True)

Valid search query keywords can be found at the `Copernicus Open Access Hub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.

Authentication
--------------

The Copernicus Open Access Hub and probably most Data Hubs require authentication.
You can provide your credentials with :class:`SentinelAPI(\<your username\>, \<your password\>) <sentinel.SentinelAPI>`. 
Alternatively, you can use :class:`SentinelAPI(None, None) <sentinel.SentinelAPI>` and enter your credentials in a 
file `.netrc` in your user home directory in the following form:

.. code-block:: text

  machine apihub.copernicus.eu
  login <your username>
  password <your password>

Either way, if you get an error 401 Unauthorized, your credentials were wrong or not yet 
active for the endpoint you are contacting.

Sorting & Filtering
-------------------

In addition to the `search query keywords <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_
sentinelsat allows filtering and sorting of search results before download. To simplify these
operations sentinelsat offers the convenience functions :meth:`~sentinel.SentinelAPI.to_geojson()`,
:meth:`~sentinel.sentinel.SentinelAPI.to_dataframe()` and :meth:`~sentinel.SentinelAPI.to_geodataframe()` which return the
search results as a GeoJSON object, Pandas DataFrame or a GeoPandas GeoDataFrame, respectively.
:meth:`~sentinel.SentinelAPI.to_dataframe()` and :meth:`~sentinel.SentinelAPI.to_geodataframe()` require `pandas
<https://pandas.pydata.org/>`_ and `geopandas <http://geopandas.org/>`_ to be installed,
respectively.


In this example we query Sentinel-2 scenes over a location and convert the query results to a Pandas DataFrame. The DataFrame is then sorted by cloud cover
and ingestion date. We limit the query to first 5 results within our timespan and download them,
starting with the least cloudy scene. Filtering can be done with
all data types, as long as you pass the `id` to the download function.

.. code-block:: python

  # connect to the API
  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
  from datetime import date

  api = SentinelAPI('user', 'password', 'https://apihub.copernicus.eu/apihub')

  # search by polygon, time, and SciHub query keywords
  footprint = geojson_to_wkt(read_geojson('map.geojson'))
  products = api.query(footprint,
                       date=('20151219', date(2015, 12, 29)),
                       platformname='Sentinel-2')

  # convert to Pandas DataFrame
  products_df = api.to_dataframe(products)

  # sort and limit to first 5 sorted products
  products_df_sorted = products_df.sort_values(['cloudcoverpercentage', 'ingestiondate'], ascending=[True, True])
  products_df_sorted = products_df_sorted.head(5)

  # download sorted and reduced products
  api.download_all(products_df_sorted.index)

Getting Product Metadata
------------------------

Sentinelsat provides two methods for retrieving product metadata from the server, one for each
API offered by the Copernicus Open Access Hub:

- :meth:`~sentinel.SentinelAPI.query()` for `OpenSearch (Solr) <https://scihub.copernicus.eu/userguide/5APIsAndBatchScripting#Open_Search>`_,
  which supports filtering products by their attributes and returns metadata for all matched
  products at once.
- :meth:`~sentinel.SentinelAPI.get_product_odata()` for `OData <https://scihub.copernicus.eu/userguide/5APIsAndBatchScripting#Open_Data_Protocol_OData>`_,
  which can be queried one product at a time but provides the full metadata available for each
  product, as well as information about the product file such as the file size and checksum, which
  are not available from OpenSearch.

Both methods return a dictionary containing the metadata items. More specifically, :meth:`~sentinel.SentinelAPI.query()`
returns a dictionary with an entry for each returned product with its ID as the key and the
attributes' dictionary as the value.

All of the attributes returned by the OpenSearch API have a corresponding but differently named
attribute in the OData's full metadata response. See the DataHubSystem's metadata definition files
to find the exact mapping between them (OpenSearch attributes have a `<solrField>` tag added):

- `Sentinel-1 attributes <https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-1/src/main/resources/META-INF/sentinel-1.owl>`_
- `Sentinel-2 attributes <https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-2/src/main/resources/META-INF/sentinel-2.owl>`_
- `Sentinel-3 attributes <https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-3/src/main/resources/META-INF/sentinel-3.owl>`_

OpenSearch example
^^^^^^^^^^^^^^^^^^

.. code-block:: python

  >>> api.query(date=('NOW-8HOURS', 'NOW'), producttype='SLC')
  OrderedDict([('04548172-c64a-418f-8e83-7a4d148adf1e',
                {'acquisitiontype': 'NOMINAL',
                 'beginposition': datetime.datetime(2017, 4, 25, 15, 56, 12, 814000),
                 'endposition': datetime.datetime(2017, 4, 25, 15, 56, 39, 758000),
                 'filename': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF.SAFE',
                 'footprint': 'POLYGON ((34.322010 0.401648,36.540989 0.876987,36.884121 -0.747357,34.664474 -1.227940,34.322010 0.401648))',
                 'format': 'SAFE',
                 'gmlfootprint': '<gml:Polygon srsName="http://www.opengis.net/gml/srs/epsg.xml#4326" xmlns:gml="http://www.opengis.net/gml">\n   <gml:outerBoundaryIs>\n      <gml:LinearRing>\n         <gml:coordinates>0.401648,34.322010 0.876987,36.540989 -0.747357,36.884121 -1.227940,34.664474 0.401648,34.322010</gml:coordinates>\n      </gml:LinearRing>\n   </gml:outerBoundaryIs>\n</gml:Polygon>',
                 'identifier': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF',
                 'ingestiondate': datetime.datetime(2017, 4, 25, 19, 23, 45, 956000),
                 'instrumentname': 'Synthetic Aperture Radar (C-band)',
                 'instrumentshortname': 'SAR-C SAR',
                 'lastorbitnumber': 16302,
                 'lastrelativeorbitnumber': 130,
                 'link': "https://apihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/$value",
                 'link_alternative': "https://apihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/",
                 'link_icon': "https://apihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/Products('Quicklook')/$value",
                 'missiondatatakeid': 110481,
                 'orbitdirection': 'ASCENDING',
                 'orbitnumber': 16302,
                 'platformidentifier': '2014-016A',
                 'platformname': 'Sentinel-1',
                 'polarisationmode': 'VV VH',
                 'productclass': 'S',
                 'producttype': 'SLC',
                 'relativeorbitnumber': 130,
                 'sensoroperationalmode': 'IW',
                 'size': '7.1 GB',
                 'slicenumber': 8,
                 'status': 'ARCHIVED',
                 'summary': 'Date: 2017-04-25T15:56:12.814Z, Instrument: SAR-C SAR, Mode: VV VH, Satellite: Sentinel-1, Size: 7.1 GB',
                 'swathidentifier': 'IW1 IW2 IW3',
                 'title': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF',
                 'uuid': '04548172-c64a-418f-8e83-7a4d148adf1e'}),
  ...

OData example
^^^^^^^^^^^^^

Only the most basic information available from the OData API is returned by default, if
`full=True` is not set. The full metadata query response is quite large and not always required,
so it is not requested by default.

.. code-block:: python

  >>> api.get_product_odata('04548172-c64a-418f-8e83-7a4d148adf1e')
  {'date': datetime.datetime(2017, 4, 25, 15, 56, 12, 814000),
   'footprint': 'POLYGON((34.322010 0.401648,36.540989 0.876987,36.884121 -0.747357,34.664474 -1.227940,34.322010 0.401648))',
   'id': '04548172-c64a-418f-8e83-7a4d148adf1e',
   'md5': 'E5855D1C974171D33EE4BC08B9D221AE',
   'size': 4633501134,
   'title': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF',
   'url': "https://apihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/$value"}


With `full=True` we receive the full metadata available for the product.

.. code-block:: python

  >>> api.get_product_odata('04548172-c64a-418f-8e83-7a4d148adf1e', full=True)
  {'Acquisition Type': 'NOMINAL',
   'Carrier rocket': 'Soyuz',
   'Cycle number': 107,
   'Date': datetime.datetime(2017, 4, 25, 15, 56, 12, 814000),
   'Filename': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF.SAFE',
   'Footprint': '<gml:Polygon srsName="http://www.opengis.net/gml/srs/epsg.xml#4326" xmlns:gml="http://www.opengis.net/gml">\n   <gml:outerBoundaryIs>\n      <gml:LinearRing>\n         <gml:coordinates>0.401648,34.322010 0.876987,36.540989 -0.747357,36.884121 -1.227940,34.664474 0.401648,34.322010</gml:coordinates>\n      </gml:LinearRing>\n   </gml:outerBoundaryIs>\n</gml:Polygon>',
   'Format': 'SAFE',
   'Identifier': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF',
   'Ingestion Date': datetime.datetime(2017, 4, 25, 19, 23, 45, 956000),
   'Instrument': 'SAR-C',
   'Instrument abbreviation': 'SAR-C SAR',
   'Instrument description': '<a target="_blank" href="https://sentinel.esa.int/web/sentinel/missions/sentinel-1">https://sentinel.esa.int/web/sentinel/missions/sentinel-1</a>',
   'Instrument description text': 'The SAR Antenna Subsystem (SAS) is developed and build by AstriumGmbH. It is a large foldable planar phased array antenna, which isformed by a centre panel and two antenna side wings. In deployedconfiguration the antenna has an overall aperture of 12.3 x 0.84 m.The antenna provides a fast electronic scanning capability inazimuth and elevation and is based on low loss and highly stablewaveguide radiators build in carbon fibre technology, which arealready successfully used by the TerraSAR-X radar imaging mission.The SAR Electronic Subsystem (SES) is developed and build byAstrium Ltd. It provides all radar control, IF/ RF signalgeneration and receive data handling functions for the SARInstrument. The fully redundant SES is based on a channelisedarchitecture with one transmit and two receive chains, providing amodular approach to the generation and reception of wide-bandsignals and the handling of multi-polarisation modes. One keyfeature is the implementation of the Flexible Dynamic BlockAdaptive Quantisation (FD-BAQ) data compression concept, whichallows an efficient use of on-board storage resources and minimisesdownlink times.',
   'Instrument mode': 'IW',
   'Instrument name': 'Synthetic Aperture Radar (C-band)',
   'Instrument swath': 'IW1 IW2 IW3',
   'JTS footprint': 'POLYGON ((34.322010 0.401648,36.540989 0.876987,36.884121 -0.747357,34.664474 -1.227940,34.322010 0.401648))',
   'Launch date': 'April 3rd, 2014',
   'Mission datatake id': 110481,
   'Mission type': 'Earth observation',
   'Mode': 'IW',
   'NSSDC identifier': '2014-016A',
   'Operator': 'European Space Agency',
   'Orbit number (start)': 16302,
   'Orbit number (stop)': 16302,
   'Pass direction': 'ASCENDING',
   'Phase identifier': 1,
   'Polarisation': 'VV VH',
   'Product class': 'S',
   'Product class description': 'SAR Standard L1 Product',
   'Product composition': 'Slice',
   'Product level': 'L1',
   'Product type': 'SLC',
   'Relative orbit (start)': 130,
   'Relative orbit (stop)': 130,
   'Satellite': 'Sentinel-1',
   'Satellite description': '<a target="_blank" href="https://sentinel.esa.int/web/sentinel/missions/sentinel-1">https://sentinel.esa.int/web/sentinel/missions/sentinel-1</a>',
   'Satellite name': 'Sentinel-1',
   'Satellite number': 'A',
   'Sensing start': datetime.datetime(2017, 4, 25, 15, 56, 12, 814000),
   'Sensing stop': datetime.datetime(2017, 4, 25, 15, 56, 39, 758000),
   'Size': '7.1 GB',
   'Slice number': 8,
   'Start relative orbit number': 130,
   'Status': 'ARCHIVED',
   'Stop relative orbit number': 130,
   'Timeliness Category': 'Fast-24h',
   'date': datetime.datetime(2017, 4, 25, 15, 56, 12, 814000),
   'footprint': 'POLYGON((34.322010 0.401648,36.540989 0.876987,36.884121 -0.747357,34.664474 -1.227940,34.322010 0.401648))',
   'id': '04548172-c64a-418f-8e83-7a4d148adf1e',
   'md5': 'E5855D1C974171D33EE4BC08B9D221AE',
   'size': 4633501134,
   'title': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF',
   'url': "https://apihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/$value"}


LTA-Products
------------

Copernicus Open Access Hub no longer stores all products online for immediate retrieval.
Offline products can be requested from the `Long Term Archive (LTA) <https://scihub.copernicus.eu/userguide/LongTermArchive>`_ and should become available within 24 hours.
Copernicus Open Access Hub's quota currently permits users to request an offline product every 30 minutes.

A product's availability can be checked with a regular OData query by evaluating the ``Online`` property value
or by using the :meth:`~sentinel.SentinelAPI.is_online()` convenience method.

The retrieval of offline products from the LTA can be triggered using :meth:`~sentinel.SentinelAPI.trigger_offline_retrieval()`.

.. code-block:: python

    product_info = api.get_product_odata(<product_id>)
    is_online = product_info['Online']
    # or
    is_online = api.is_online(<product_id>)

    if is_online:
        print(f'Product {<product_id>} is online. Starting download.')
        api.download(<product_id>)
    else:
        print(f'Product {<product_id>} is not online.')
        api.trigger_offline_retrieval(<product_id>)

When trying to download an offline product with :meth:`~sentinel.SentinelAPI.download` it will trigger its retrieval from the LTA and raise an ``LTATriggered`` exception.

Given a list of offline and online products, :meth:`~sentinel.SentinelAPI.download_all` will download online products, while concurrently triggering the retrieval of offline products from the LTA in the background.
:meth:`~sentinel.SentinelAPI.download_all` terminates when all products have been retrieved from the LTA and downloaded.
If you wish to avoid the possibly lengthy retrieval process of offline products, you can either set the :attr:`~sentinel.SentinelAPI.lta_timeout` parameter to a low value or filter the list of products based on the :meth:`~sentinel.SentinelAPI.is_online()` status beforehand.

Logging
-------

Sentinelsat logs to :mod:`sentinelsat` and the API to :class:`sentinelsat.SentinelAPI`.

There is no predefined `logging <https://docs.python.org/3/library/logging.html>`_ handler,
so in order to have your script print the log messages, either use :class:`logging.baseConfig`

.. code-block:: python

  import logging

  logging.basicConfig(format='%(message)s', level='INFO')


or add a custom handler for :mod:`sentinelsat` (as implemented in `cli.py`)

.. code-block:: python

  import logging

  logger = logging.getLogger('sentinelsat')
  logger.setLevel('INFO')

  h = logging.StreamHandler()
  h.setLevel('INFO')
  fmt = logging.Formatter('%(message)s')
  h.setFormatter(fmt)
  logger.addHandler(h)


Downloading parts of products
-----------------------------

Both :meth:`~sentinel.SentinelAPI.download` and :meth:`~sentinel.SentinelAPI.download_all`
include a ``nodefilter`` parameter that can be used to specify a subset of files within the product
that should be downloaded, skipping the rest. 
The downloaded files will be written to disk as individual files instead of a single archive file.
This functionality makes use of the `node selection feature`_ of the OData_ Web API.

.. code-block:: python

  from sentinelsat import SentinelAPI, make_path_filter

  # define the filter function to select files (to be excluded in this case)
  path_filter = make_path_filter("*measurement/*", exclude=True)

  # connect to the API
  api = SentinelProductAPI("user", "password")

  # download a single product excluding measurement files
  api.download(<product_id>, nodefilter=path_filter)

Of course it also works for multiple products, too:

.. code-block:: python

  # download a multiple products excluding measurement files
  api.download_all(<products>, nodefilter=path_filter)

The example above downloads all files in each of the requested products only
*excluding* (large) measurements files.
This can be useful for analyses exclusively based on product annotations
(including calibration annotations) or, e.g., to download the KML preview
included in the product.

The file selection is implemented by specifying a *nodefilter* function that
is called for each file (except for the manifest, which is always downloaded)
in the requested products and returns ``True`` if the file have to be downloaded,
``False`` otherwise.

The *nodefilter* function has the following signature:

.. code-block:: python

  def nodefilter(node_info: dict) -> bool:
      ...

The *node_info* parameter is a dictionary containing (at least) the following
keys:

:url:
    the URL to download the product file node
:node_path:
    the *path* within the product (e.g. "./preview/map-overlay.kml")
:size:
    the file size in bytes (int)
:md5:
    the file's MD5 checksum

In the example above it has been used an helper function
(:func:`sentinelsat.products.make_path_filter`), provided by the
:mod:`sentinelsat.products` module, that generates *nodefilter* functions
based on glob expressions applied to the *node_path* value.

The following code:

.. code-block:: python

  path_filter = make_path_filter("*measurement/*", exclude=True)

is more or less equivalent to:

.. code-block:: python

  import fnmatch

  def path_filter(node_info):
    return fnmatch.fnmatch(node_info["node_path"].lower(), pattern)

The :mod:`sentinelsat` product node API also provides:

* the :func:`sentinelsat.products.make_size_filter` helper to build filters
  based on the file size and
* the pre-build :func:`sentinelsat.products.all_nodes_filter` *nodefilter*
  function to download all files.
  This function can be used to download the entire Sentinel product as a
  directory instead of downloading a single zip archive.

Of course the user can write their own *nodefilter* functions if necessary.


.. _`node selection feature`: https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/ODataAPI#Discover_Product_Nodes

More Examples
-------------

Search Sentinel-2 L1C by tile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To search for recent Sentinel-2 L1C imagery by MGRS tile, you can use the `tileid` parameter:

.. code-block:: python

  from collections import OrderedDict
  from sentinelsat import SentinelAPI

  api = SentinelAPI('user', 'password')

  tiles = ['33VUC', '33UUB']

  query_kwargs = {
          'platformname': 'Sentinel-2',
          'producttype': 'S2MSI1C',
          'date': ('NOW-14DAYS', 'NOW')}

  products = OrderedDict()
  for tile in tiles:
      kw = query_kwargs.copy()
      kw['tileid'] = tile
      pp = api.query(**kw)
      products.update(pp)

  api.download_all(products)

NB: Older products may not be found with the `tileid` parameter. On the Copernicus Open Access Hub,
it seems to be available for most L1C products (product type S2MSI1C) from recent years,
but this differs by region, too.
To be on the safe side, combine the `tileid` search with a `filename` pattern search:

.. code-block:: python

  kw = query_kwargs.copy()
  kw['raw'] = f'tileid:{tile} OR filename:*_T{tile}_*'
  pp = api.query(**kw)


Download only some of the channels of a Sentinel-1 product
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some cases the user may be interested only to a specific sub-swath and/or
polarization of Sentinel1 SLC products (e.g. for an interferometric analysis).

The following *nodefilter* function only downloads "HH" polarization
measurement files for sub-swaths "EW1" and "EW2":

.. code-block:: python

  path_filter = make_path_filter("*s1?-ew[12]-slc-hh-*.tiff")

Considering that e.g. a Dual Pol Extended Wide Swath Sentinel-1 product
includes 2 measurement files for each of the 5 sub-swath the above filter
allows to reduce consistently the amount of data to be downloaded
(form 10 to 2 TIFF files approx 700MB each).

.. code-block:: python

    api.download_all(<products>, nodefilter=path_filter)
