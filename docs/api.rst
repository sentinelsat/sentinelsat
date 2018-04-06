.. _api:

Python API
==========

Quickstart
----------

.. code-block:: python

  # connect to the API
  from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
  from datetime import date

  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

  # download single scene by known product id
  api.download(<product_id>)

  # search by polygon, time, and SciHub query keywords
  footprint = geojson_to_wkt(read_geojson('map.geojson'))
  products = api.query(footprint,
                       date=('20151219', date(2015, 12, 29)),
                       platformname='Sentinel-2',
                       cloudcoverpercentage=(0, 30))

  # download all results from the search
  api.download_all(products)

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
  from datetime import date

  api = SentinelAPI('user', 'password', 'https://scihub.copernicus.eu/dhus')

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
  api.download_all(products_df_sorted['id'])

Getting Product Metadata
------------------------

Sentinelsat provides two methods for retrieving product metadata from the server, one for each
API offered by the Copernicus Open Access Hub:

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

More Examples
-------------

Search Sentinel 2 by tile
^^^^^^^^^^^^^^^^^^^^^^^^^

To search for recent Sentinel 2 imagery by MGRS tile, use the `tileid` parameter:

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
      kw['tileid'] = tile  # products after 2017-03-31
      pp = api.query(**kw)
      products.update(pp)

  api.download_all(products)

NB: The `tileid` parameter only works for products from April 2017 onward due to
missing metadata in SciHub's DHuS catalogue. Before that, but only from
December 2016 onward (i.e. for single-tile products), you can use a `filename` pattern instead:

.. code-block:: python

  kw['filename'] = '*_T{}_*'.format(tile)  # products after 2016-12-01

Exclude Products already available offline from download_all
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``SentinelAPI.download_all()`` automatically skips products that are already in the target directory (current directory
or as specified in ``directory_path``) if their folder name has not changed. In order to exclude products stored under a
different location and/or folder name, one has to manually filter the OrderedDict returned from the ``query()``
method before feeding it to ``download_all()``:

.. code-block:: python

  from sentinelsat import SentinelAPI
  import xml.etree.ElementTree as ET
  import os
  import zipfile
  import tempfile
  import time
  import re

  # make a demo folder:
  demo_folder = os.path.join(tempfile.gettempdir(),"sentinelsat_exclude_products_demo_{}".format(round(time.time())))

  # On (old) windows systems the maximum path length is restricted to 260 characters. Exceeding this limitation might
  # result in errors (cp. https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx#maxpath).
  # user "eryksun" on https://stackoverflow.com/questions/36219317/pathname-too-long-to-open/36237176
  # offers the following solution (+explanations):
  if os.name == 'nt':
    demo_folder = u"\\\\?\\" + demo_folder

  os.mkdir(demo_folder)
  print("Watch the following folder to see what happens during the demo:\n{}".format(demo_folder))

  # set up a demo query including Sentinel 1 and 2 products
  api = SentinelAPI('user','password')
  demo_query = api.query(filename = "S2A_OPER_PRD_MSIL1C_PDMC_20161013T075059_R111_V20161012T161812_20161012T161807.SAFE")
  demo_query.update(api.query(filename = "S1A_WV_OCN__2SSV_20150526T081641_20150526T082418_006090_007E3E_104C.SAFE"))

  # download the products in the demo_query dictionary
  downloaded = api.download_all(demo_query, directory_path=demo_folder)
  zip_1 = [i for i in os.listdir(demo_folder) if i.endswith(".zip")]
  print("The following zipfiles where downloaded:\n{}".format(zip_1))

  # try to download the same products a second time
  downloaded = api.download_all(demo_query, directory_path=demo_folder)
  zip_2 = [i for i in os.listdir(demo_folder) if i.endswith(".zip") and i not in zip_1]
  print("Trying to download the same products again automatically skips all products so nothing is downloaded:\n{}".format(zip_2))

  # unzip and rename products downloaded using the demo_query
  zip_1_fullpath = [os.path.join(demo_folder,f) for f in zip_1]
  unzipped_renamed = []
  for p in zip_1_fullpath:
      # unzip
      with zipfile.ZipFile(p, 'r') as zip_f:
          zip_f.extractall(path = demo_folder)
      # remove zipfile
      os.remove(p)

      # rename based on sensor prefix and acquisition time:
      path_unzipped = p.replace(".zip",".SAFE")
      prefix,_,acquisition = (re.findall("(S1A|S2A)(.*)(_\d{8}T\d{6})",path_unzipped))[0]
      path_renamed = os.path.join(demo_folder,prefix + acquisition)
      os.rename(path_unzipped,path_renamed)
      unzipped_renamed.append(path_renamed)

  # Since the demo_folder now contains products with custom names, sentinelsat cannot exclude them from the download
  # automatically and would download the products all over again (try it if you like by uncommenting the following):
  # downloaded = api.download_all(demo_query, directory_path=demo_folder)

  # The trick is to figure out the original filenames. Where to find the filenames depends on the sensor and the product
  # format. Here are some common places and how to obtain it:
  # Sentinel 1: in the filename of the -report- pdf in the root folder
  # Sentinel 2: in the INSPIRE.xml in the root folder
  skip_titles = []
  for f in unzipped_renamed:
      title_file = ([i for i in os.listdir(f) if i.endswith("pdf") or i == "INSPIRE.xml"])[0]

      if title_file.endswith("pdf"):
          # take first part of the report pdf filename
          skip_titles.append(title_file.split("-report-")[0])
      elif title_file == "INSPIRE.xml":
          # parse the INSPIRE.xml document:
          title_file = os.path.join(f, title_file)
          namespaces = {"gco": "http://www.isotc211.org/2005/gco", "gmd": "http://www.isotc211.org/2005/gmd"}
          path = "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString"
          dom = ET.parse(title_file)
          skip_titles.append(dom.find(path, namespaces).text)

  # Now lets say we have a new query that includes one additional product
  demo_query.update(api.query(filename = "S1A_WV_OCN__2SSH_20150603T092625_20150603T093332_006207_008194_521E.SAFE"))

  # If we want to skip the products already available offline we have to filter the query using the filenames we just
  # recorded in the skip_titles list
  demo_query_filtered = {k:v for k,v in demo_query.items() if v['filename'] not in skip_titles}

  # Now we can pass the filtered query to the download_all method and as you can see the other products are not
  # downloaded again even though there do not have their original filenames:
  downloaded = api.download_all(demo_query_filtered, directory_path=demo_folder)
  zip_new = [i for i in os.listdir(demo_folder) if i.endswith(".zip")]
  print("The following zipfiles where downloaded in the updated and filtered query:\n{}".format(zip_1))

API
---

.. automodule:: sentinelsat

.. autoclass:: SentinelAPI
    :members:

.. autofunction:: read_geojson

.. autofunction:: geojson_to_wkt

Exceptions
----------

.. autoexception:: SentinelAPIError

.. autoexception:: InvalidChecksumError
