.. _api:

Python API
==========

Quickstart
----------

.. code-block:: python

  # connect to the API
  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and SciHub query keywords
  footprint = geojson_to_wkt(read_geojson('map.geojson'))
  products = api.query(footprint,
                       '20151219', date(2015, 12, 29),
                       platformname = 'Sentinel-2',
                       cloudcoverpercentage = '[0 TO 30]')

  # download all results from the search
  api.download_all(products)

  # GeoJSON FeatureCollection containing footprints and metadata of the scenes
  api.to_geojson(products)

  # GeoPandas GeoDataFrame with the metadata of the scenes and the footprints as geometries
  api.to_geopandas(products)

  # Get basic information about the product: its title, file size, MD5 sum, date, footprint and
  # its download url
  api.get_product_odata(<product_id>)

  # Get the product's full metadata available on the server
  api.get_product_odata(<product_id>, full=True)

Valid search query keywords can be found at the `ESA SciHub documentation
<https://scihub.copernicus.eu/userguide/3FullTextSearch>`_.

Sorting & Filtering
-------------------

In addition to the `search query keywords <https://scihub.copernicus.eu/userguide/3FullTextSearch>`_ sentinelsat allows
filtering and sorting of search results before download. To simplify these operations sentinelsat offers the convenience
functions ``to_geojson()``, ``to_dataframe()`` and ``to_geodataframe()`` which return the search results as
a GeoJSON object, Pandas DataFrame or a GeoPandas GeoDataFrame, respectively. ``to_dataframe()``
and ``to_geodataframe()`` require ``pandas`` and ``geopandas`` to be installed, respectively.

In this example we query Sentinel-2 scenes over a location and convert the query results to a Pandas DataFrame. The DataFrame is then sorted by cloud cover
and ingestion date. We limit the query to first 5 results within our timespan and download them,
starting with the least cloudy scene. Filtering can be done with
all data types, as long as you pass the ``id`` to the download function.

.. code-block:: python

  # connect to the API
  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt

  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # search by polygon, time, and SciHub query keywords
  footprint = geojson_to_wkt(read_geojson('map.geojson'))
  products = api.query(footprint,
                       '20151219', date(2015, 12, 29),
                       platformname = 'Sentinel-2')

  # convert to Pandas DataFrame
  products_df = api.to_dataframe(products)

  # sort and limit to first 5 sorted products
  products_df_sorted = products_df.sort_values(['cloudcoverpercentage', 'ingestiondate'], ascending=[True, True])
  products_df_sorted = products_df_sorted.head(5)

  # download sorted and reduced products
  api.download_all(products_df_sorted['id'])

Getting Product Metadata
------------------------

Sentinelsat provides two methods for retrieving metadata for products from the server, one for each
API provided by SciHub:

- ``query()`` for `OpenSearch (Solr) <https://scihub.copernicus.eu/userguide/5APIsAndBatchScripting#Open_Search>`_,
  which supports filtering products by their attributes and returns metadata for all matched
  products at once.
- ``get_product_odata()`` for `OData <https://scihub.copernicus.eu/userguide/5APIsAndBatchScripting#Open_Data_Protocol_OData>`_,
  which can be queried one product at a time but provides the full metadata available for each
  product, as well as information about the product file such as the file size and checksum, which
  are not available from OpenSearch.

Both methods return a dictionary containing the metadata items. More specifically, ``query()``
returns a dictionary with an entry for each returned product with its ID as the key and the
attributes' dictionary as the value.

All of the attributes returned by the OpenSearch API have a corresponding but differently named
attribute in the OData's full metadata response. See the DataHubSystem's metadata definition files
to find the exact mapping between them (OpenSearch attributes have a ``<solrField>`` tag added):
- `Sentinel-1 attributes <https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-1/src/main/resources/META-INF/sentinel-1.owl>`_
- `Sentinel-2 attributes <https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-2/src/main/resources/META-INF/sentinel-2.owl>`_
- `Sentinel-3 attributes <https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-3/src/main/resources/META-INF/sentinel-3.owl>`_

OpenSearch example
^^^^^^^^^^^^^^^^^^

.. code-block:: python

  >>> api.query(initial_date='NOW-8HOURS', producttype='SLC')
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
                 'link': "https://scihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/$value",
                 'link_alternative': "https://scihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/",
                 'link_icon': "https://scihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/Products('Quicklook')/$value",
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
``full=True`` is not set. The full metadata query response is quite large and not always nrequired,
so it is not requested by default.

.. code-block:: python

  >>> api.get_product_odata('04548172-c64a-418f-8e83-7a4d148adf1e')
  {'date': datetime.datetime(2017, 4, 25, 15, 56, 12, 814000),
   'footprint': 'POLYGON((34.322010 0.401648,36.540989 0.876987,36.884121 -0.747357,34.664474 -1.227940,34.322010 0.401648))',
   'id': '04548172-c64a-418f-8e83-7a4d148adf1e',
   'md5': 'E5855D1C974171D33EE4BC08B9D221AE',
   'size': 4633501134,
   'title': 'S1A_IW_SLC__1SDV_20170425T155612_20170425T155639_016302_01AF91_46FF',
   'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/$value"}


With ``full=True`` we receive the full metadata available for the product.

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
   'url': "https://scihub.copernicus.eu/apihub/odata/v1/Products('04548172-c64a-418f-8e83-7a4d148adf1e')/$value"}


Logging
-------

Sentinelsat logs to ``sentinelsat`` and the API to ``sentinelsat.SentinelAPI``.

There is no predefined `logging <https://docs.python.org/3/library/logging.html>`_ handler,
so in order to have your script print the log messages, either use ``logging.baseConfig``

.. code-block:: python

  import logging

  logging.basicConfig(format='%(message)s', level='INFO')


or add a custom handler for ``sentinelsat`` (as implemented in ``cli.py``)

.. code-block:: python

  import logging

  logger = logging.getLogger('sentinelsat')
  logger.setLevel('INFO')

  h = logging.StreamHandler()
  h.setLevel('INFO')
  fmt = logging.Formatter('%(message)s')
  h.setFormatter(fmt)
  logger.addHandler(h)


API
---

.. automodule:: sentinelsat
    :members:
