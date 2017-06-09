# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import hashlib
import logging
import re
import shutil
import xml.etree.ElementTree as ET
from collections import OrderedDict
from contextlib import closing
from datetime import date, datetime, timedelta
from os import remove
from os.path import exists, getsize, join

import geojson
import geomet.wkt
import html2text
import requests
from tqdm import tqdm

from six import string_types
from six.moves.urllib.parse import urljoin

from . import __version__ as sentinelsat_version


class SentinelAPI:
    """Class to connect to Copernicus Open Access Hub, search and download imagery.

    Parameters
    ----------
    user : string
        username for DataHub
    password : string
        password for DataHub
    api_url : string, optional
        URL of the DataHub
        defaults to 'https://scihub.copernicus.eu/apihub'

    Attributes
    ----------
    session : requests.Session object
        Session to connect to DataHub
    api_url : str
        URL to the DataHub
    page_size : int
        number of results per query page
        current value: 100 (maximum allowed on ApiHub)
    """

    logger = logging.getLogger('sentinelsat.SentinelAPI')

    def __init__(self, user, password, api_url='https://scihub.copernicus.eu/apihub/'):
        self.session = requests.Session()
        if user and password:
            self.session.auth = (user, password)
        self.api_url = api_url if api_url.endswith('/') else api_url + '/'
        self.page_size = 100
        self.user_agent = 'sentinelsat/' + sentinelsat_version
        self.session.headers['User-Agent'] = self.user_agent
        # For unit tests
        self._last_query = None
        self._last_response = None

    def query(self, area=None, initial_date='NOW-1DAY', end_date='NOW',
              order_by=None, limit=None, offset=0,
              area_relation='Intersects', **keywords):
        """Query the OpenSearch API with the coordinates of an area, a date interval
        and any other search keywords accepted by the API.

        Parameters
        ----------
        area : str, optional
            The area of interest formatted as a Well-Known Text string.
        initial_date : str or datetime, optional
            Beginning of the time interval for sensing time. Defaults to 'NOW-1DAY'.
            Either a Python datetime or a string in one of the following formats:
                - yyyy-MM-ddThh:mm:ss.SSSZ (ISO-8601)
                - yyyy-MM-ddThh:mm:ssZ
                - YYYMMdd
                - NOW
                - NOW-<n>DAY(S) (or HOUR(S), MONTH(S), etc.)
                - NOW+<n>DAY(S)
                - yyyy-MM-ddThh:mm:ssZ-<n>DAY(S)
                - NOW/DAY (or HOUR, MONTH etc.) - rounds the value to the given unit
        end_date : str or datetime, optional
            Beginning of the time interval for sensing time.  Defaults to 'NOW'.
            See initial_date for allowed format.
        order_by: str, optional
            A comma-separated list of fields to order by (on server side).
            Prefix the field name by '+' or '-' to sort in ascending or descending order, respectively.
            Ascending order is used, if prefix is omitted.
            Example: "cloudcoverpercentage, -beginposition".
        limit: int, optional
            Maximum number of products returned. Defaults to no limit.
        offset: int, optional
            The number of results to skip. Defaults to 0.
        area_relation : {'Intersection', 'Contains', 'IsWithin'}, optional
            What relation to use for testing the AOI. Case insensitive.
                - Intersects: true if the AOI and the footprint intersect (default)
                - Contains: true if the AOI is inside the footprint
                - IsWithin: true if the footprint is inside the AOI


        Other Parameters
        ----------------
        Additional keywords can be used to specify other query parameters, e.g. orbitnumber=70.

        See https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/3FullTextSearch
        for a full list of accepted parameters.

        Returns
        -------
        dict[string, dict]
            Products returned by the query as a dictionary with the product ID as the key and
            the product's attributes (a dictionary) as the value.
        """
        query = self.format_query(area, initial_date, end_date, area_relation, **keywords)
        return self.query_raw(query, order_by, limit, offset)

    @staticmethod
    def format_query(area=None, initial_date='NOW-1DAY', end_date='NOW', area_relation='Intersects', **keywords):
        """Create OpenSearch API query string
        """
        if area_relation.lower() not in {"intersects", "contains", "iswithin"}:
            raise ValueError("Incorrect AOI relation provided ({})".format(area_relation))

        query_parts = []
        if initial_date is not None and end_date is not None:
            query_parts += ['(beginPosition:[%s TO %s])' % (
                _format_query_date(initial_date),
                _format_query_date(end_date)
            )]

        if area is not None:
            query_parts += ['(footprint:"%s(%s)")' % (area_relation, area)]

        for kw in sorted(keywords):
            query_parts += ['(%s:%s)' % (kw, keywords[kw])]

        query = ' AND '.join(query_parts)
        # plus symbols would be interpreted as spaces without escaping
        query = query.replace('+', '%2B')
        return query

    def query_raw(self, query, order_by=None, limit=None, offset=0):
        """Do a full-text query on the OpenSearch API using the format specified in
           https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/3FullTextSearch

        Parameters
        ----------
        query : str
            The query string.
        order_by: str, optional
            A comma-separated list of fields to order by (on server side).
            Prefix the field name by '+' or '-' to sort in ascending or descending order, respectively.
            Ascending order is used, if prefix is omitted.
            Example: "cloudcoverpercentage, -beginposition".
        limit: int, optional
            Maximum number of products returned. Defaults to no limit.
        offset: int, optional
            The number of results to skip. Defaults to 0.

        Returns
        -------
        dict[string, dict]
            Products returned by the query as a dictionary with the product ID as the key and
            the product's attributes (a dictionary) as the value.
        """
        # plus symbols would be interpreted as spaces without escaping
        query = query.replace('+', '%2B')
        formatted_order_by = _format_order_by(order_by)
        try:
            response, count = self._load_query(query, formatted_order_by, limit, offset)
        except SentinelAPIError as e:
            # Queries with length greater than about 2700-3600 characters (depending on content) may
            # produce "HTTP status 500 Internal Server Error"
            factor = self.check_query_length(query)
            if e.response.status_code == 500 and not e.msg and factor > 0.95 :
                e.msg = ("The query likely failed due to its length "
                         "({:.1%} of the limit)".format(factor))
            e.__cause__ = None
            raise e
        self.logger.info("Found {} products".format(count))
        return _parse_opensearch_response(response)

    def count(self, query):
        """Get the number of products matching a query.

        This is a significantly more efficient alternative to doing len(api.query_raw(...)),
        which can take minutes to run for queries matching thousands of products.

        Parameters
        ----------
        query : str
            The query string.

        Returns
        -------
        int
            The number of products matching a query.
        """
        _, total_count = self._load_query(query, limit=0)
        return total_count

    def _load_query(self, query, order_by=None, limit=None, offset=0):
        # store last query (for testing)
        self._last_query = query

        # load query results
        url = self._format_url(order_by, limit, offset)
        response = self.session.post(url, {'q': query}, auth=self.session.auth)
        _check_scihub_response(response)

        # store last status code (for testing)
        self._last_response = response

        # parse response content
        try:
            json_feed = response.json()['feed']
            total_results = int(json_feed['opensearch:totalResults'])
        except (ValueError, KeyError):
            raise SentinelAPIError('API response not valid. JSON decoding failed.', response)

        products = json_feed.get('entry', [])
        # this verification is necessary because if the query returns only
        # one product, self.products will be a dict not a list
        if isinstance(products, dict):
            products = [products]

        # repeat query until all results have been loaded
        new_limit = limit
        if limit is not None:
            new_limit -= len(products)
            if new_limit <= 0:
                return products, total_results
        new_offset = offset + self.page_size
        if total_results >= new_offset:
            products += self._load_query(query, limit=new_limit, offset=new_offset)[0]
        return products, total_results

    def _format_url(self, order_by=None, limit=None, offset=0):
        if limit is None:
            limit = self.page_size
        limit = min(limit, self.page_size)
        url = 'search?format=json&rows={}'.format(limit)
        url += '&start={}'.format(offset)
        if order_by:
            url += '&orderby={}'.format(order_by)
        return urljoin(self.api_url, url)

    @staticmethod
    def to_geojson(products):
        """Return the products from a query response as a GeoJSON with the values in their
        appropriate Python types.
        """
        feature_list = []
        for i, (product_id, props) in enumerate(products.items()):
            props = props.copy()
            props['id'] = product_id
            poly = geomet.wkt.loads(props['footprint'])
            del props['footprint']
            del props['gmlfootprint']
            # Fix "'datetime' is not JSON serializable"
            for k, v in props.items():
                if isinstance(v, (date, datetime)):
                    props[k] = v.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            feature_list.append(
                geojson.Feature(geometry=poly, id=i, properties=props)
            )
        return geojson.FeatureCollection(feature_list)

    @staticmethod
    def to_dataframe(products):
        """Return the products from a query response as a Pandas DataFrame
        with the values in their appropriate Python types.
        """
        import pandas as pd

        return pd.DataFrame.from_dict(products, orient='index')

    @staticmethod
    def to_geodataframe(products):
        """Return the products from a query response as a GeoPandas GeoDataFrame
        with the values in their appropriate Python types.
        """
        import geopandas as gpd
        import shapely.wkt

        df = SentinelAPI.to_dataframe(products)
        crs = {'init': 'epsg:4326'}  # WGS84
        geometry = [shapely.wkt.loads(fp) for fp in df['footprint']]
        # remove useless columns
        df.drop(['footprint', 'gmlfootprint'], axis=1, inplace=True)
        return gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

    def get_product_odata(self, id, full=False):
        """Access OData API to get info about a product.

        Returns a dict containing the id, title, size, md5sum, date, footprint and download url
        of the product. The date field corresponds to the Start ContentDate value.

        If ``full`` is set to True, then the full, detailed metadata of the product is returned
        in addition to the above. For a mapping between the OpenSearch (Solr) and OData
        attribute names see the following definition files:
        https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-1/src/main/resources/META-INF/sentinel-1.owl
        https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-2/src/main/resources/META-INF/sentinel-2.owl
        https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-3/src/main/resources/META-INF/sentinel-3.owl

        Parameters
        ----------
        id : string
            The ID of the product to query
        full : bool
            Whether to get the full metadata for the Product

        Returns
        -------
        dict[str, Any]
            A dictionary with an item for each metadata attribute
        """
        url = urljoin(self.api_url, "odata/v1/Products('{}')?$format=json".format(id))
        if full:
            url += '&$expand=Attributes'
        response = self.session.get(url, auth=self.session.auth)
        _check_scihub_response(response)
        values = _parse_odata_response(response.json()['d'])
        return values

    def download(self, id, directory_path='.', checksum=False):
        """Download a product.

        Uses the filename on the server for the downloaded file, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.zip".

        Incomplete downloads are continued and complete files are skipped.

        Parameters
        ----------
        id : string
            UUID of the product, e.g. 'a8dd0cfd-613e-45ce-868c-d79177b916ed'
        directory_path : string, optional
            Where the file will be downloaded
        checksum : bool, optional
            If True, verify the downloaded file's integrity by checking its MD5 checksum.
            Throws InvalidChecksumError if the checksum does not match.
            Defaults to False.

        Returns
        -------
        product_info : dict
            Dictionary containing the product's info from get_product_info() as well as the path on disk.

        Raises
        ------
        InvalidChecksumError
            If the MD5 checksum does not match the checksum on the server.
        """
        product_info = self.get_product_odata(id)
        path = join(directory_path, product_info['title'] + '.zip')
        product_info['path'] = path
        product_info['downloaded_bytes'] = 0

        self.logger.info('Downloading %s to %s' % (id, path))

        if exists(path):
            # We assume that the product has been downloaded and is complete
            return product_info

        # Use a temporary file for downloading
        temp_path = path + '.incomplete'

        skip_download = False
        if exists(temp_path):
            if getsize(temp_path) > product_info['size']:
                self.logger.warning(
                    "Existing incomplete file {} is larger than the expected final size"
                    " ({} vs {} bytes). Deleting it.".format(
                    str(temp_path), getsize(temp_path), product_info['size']))
                remove(temp_path)
            elif getsize(temp_path) == product_info['size']:
                if _md5_compare(temp_path, product_info['md5']):
                    skip_download = True
                else:
                    # Log a warning since this should never happen
                    self.logger.warning(
                        "Existing incomplete file {} appears to be fully downloaded but "
                        "its checksum is incorrect. Deleting it.".format(
                            str(temp_path), getsize(temp_path), product_info['size']))
                    remove(temp_path)
            else:
                # continue downloading
                self.logger.info("Download will resume from existing incomplete file "
                                 "{}.".format(temp_path))
                pass

        if not skip_download:
            # Store the number of downloaded bytes for unit tests
            product_info['downloaded_bytes'] = _download(
                product_info['url'], temp_path, self.session, product_info['size'])

        # Check integrity with MD5 checksum
        if checksum is True:
            if not _md5_compare(temp_path, product_info['md5']):
                remove(temp_path)
                raise InvalidChecksumError('File corrupt: checksums do not match')

        # Download successful, rename the temporary file to its proper name
        shutil.move(temp_path, path)
        return product_info

    def download_all(self, products, directory_path='.', max_attempts=10, checksum=False):
        """Download a list of products.

        Takes a list of product IDs as input. This means that the return value of query() can be
        passed directly to this method.

        File names on the server are used for the downloaded files, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.zip".

        In case of interruptions or other exceptions, downloading will restart from where it left off.
        Downloading is attempted at most max_attempts times to avoid getting stuck with unrecoverable errors.

        Parameters
        ----------
        products : list
            List of product IDs
        directory_path : string
            Directory where the downloaded files will be downloaded
        max_attempts : int, optional
            Number of allowed retries before giving up downloading a product. Defaults to 10.

        Other Parameters
        ----------------
        See download().

        Raises
        ------
        Raises the most recent downloading exception if all downloads failed.

        Returns
        -------
        dict[string, dict]
            A dictionary containing the return value from download() for each successfully downloaded product.
        set[string]
            The list of products that failed to download.
        """
        product_ids = list(products)
        self.logger.info("Will download %d products" % len(product_ids))
        return_values = OrderedDict()
        last_exception = None
        for i, product_id in enumerate(products):
            for attempt_num in range(max_attempts):
                try:
                    product_info = self.download(product_id, directory_path, checksum)
                    return_values[product_id] = product_info
                    break
                except (KeyboardInterrupt, SystemExit):
                    raise
                except InvalidChecksumError as e:
                    last_exception = e
                    self.logger.warning(
                        "Invalid checksum. The downloaded file for '{}' is corrupted.".format(product_id))
                except Exception as e:
                    last_exception = e
                    self.logger.exception("There was an error downloading %s" % product_id)
            self.logger.info("{}/{} products downloaded".format(i + 1, len(product_ids)))
        failed = set(products) - set(return_values)

        if len(failed) == len(product_ids) and last_exception is not None:
            raise last_exception
        return return_values, failed

    @staticmethod
    def get_products_size(products):
        """Return the total file size in GB of all products in the OpenSearch response"""
        size_total = 0
        for title, props in products.items():
            size_product = props["size"]
            size_value = float(size_product.split(" ")[0])
            size_unit = str(size_product.split(" ")[1])
            if size_unit == "MB":
                size_value /= 1024.
            if size_unit == "KB":
                size_value /= 1024. * 1024.
            size_total += size_value
        return round(size_total, 2)

    @staticmethod
    def check_query_length(query):
        """Determine whether a query to the OpenSearch API is too long.

        The length of a query string is limited to approximately 3893 characters but
        any special characters (that is, not alphanumeric or -_.~) are counted twice
        towards that limit.

        Parameters
        ----------
        query : str
            The query string

        Returns
        -------
        float
            Ratio of the query length to the maximum length

        Notes
        -----
        The query size limit arises from a limit on the length of the server's internal query,
        which looks like

        http://localhost:30333//solr/dhus/select?q=...
        &wt=xslt&tr=opensearch_atom.xsl&dhusLongName=Sentinels+Scientific+Data+Hub
        &dhusServer=https%3A%2F%2Fscihub.copernicus.eu%2Fapihub%2F&originalQuery=...
        &rows=100&start=0&sort=ingestiondate+desc

        This function will estimate the length of the "q" and "originalQuery" parameters to
        determine whether the query will fail. Their combined length can be at most about
        7786 bytes.
        """
        # fix plus symbols for consistency with .query()
        # they would be interpreted as spaces without escaping
        query = query.replace('+', '%2B')
        # q = query.replace(" ", "%20")
        # originalQuery = quote_plus(query)
        # This can be simplified to just counting the number of special characters
        effective_length = len(query) + len(re.findall('[^-_.~0-9A-Za-z]', query))
        return effective_length / 3893


class SentinelAPIError(Exception):
    """Invalid responses from DataHub.
    """

    def __init__(self, msg=None, response=None):
        self.msg = msg
        self.response = response

    def __str__(self):
        return 'HTTP status {0} {1}: {2}'.format(
            self.response.status_code, self.response.reason,
            ('\n' if '\n' in self.msg else '') + self.msg)


class InvalidChecksumError(Exception):
    """MD5 checksum of a local file does not match the one from the server.
    """
    pass


def read_geojson(geojson_file):
    with open(geojson_file) as f:
        return geojson.load(f)


def geojson_to_wkt(geojson_obj, feature_number=0, decimals=4):
    """Convert a GeoJSON object to Well-Known Text. Intended for use with OpenSearch queries.

    In case of FeatureCollection, only one of the features is used (the first by default).
    3D points are converted to 2D.

    Parameters
    ----------
    geojson_obj : dict
        a GeoJSON object
    feature_number : int, optional
        Feature to extract polygon from (in case of MultiPolygon
        FeatureCollection), defaults to first Feature
    decimals : int, optional
        Number of decimal figures after point to round coordinate to. Defaults to 4 (about 10
        meters).

    Returns
    -------
    polygon coordinates
        string of comma separated coordinate tuples (lon, lat) to be used by SentinelAPI
    """
    if 'coordinates' in geojson_obj:
        geometry = geojson_obj
    else:
        geometry = geojson_obj['features'][feature_number]['geometry']

    def ensure_2d(geometry):
        if isinstance(geometry[0], (list, tuple)):
            return list(map(ensure_2d, geometry))
        else:
            return geometry[:2]

    # Discard z-coordinate, if it exists
    geometry['coordinates'] = ensure_2d(geometry['coordinates'])

    return geomet.wkt.dumps(geometry, decimals=decimals)


def _check_scihub_response(response, test_json=True):
    """Check that the response from server has status code 2xx and that the response is valid JSON."""
    try:
        response.raise_for_status()
        if test_json:
            response.json()
    except (requests.HTTPError, ValueError):
        msg = "Invalid API response."
        try:
            msg = response.headers['cause-message']
        except:
            try:
                msg = response.json()['error']['message']['value']
            except:
                if not response.text.strip().startswith('{'):
                    try:
                        h = html2text.HTML2Text()
                        h.ignore_images = True
                        h.ignore_anchors = True
                        msg = h.handle(response.text).strip()
                    except:
                        pass
        api_error = SentinelAPIError(msg, response)
        # Suppress "During handling of the above exception..." message
        # See PEP 409
        api_error.__cause__ = None
        raise api_error


def _format_query_date(in_date):
    """Format a date, datetime or a YYYYMMDD string input as YYYY-MM-DDThh:mm:ssZ
    or validate a string input as suitable for the full text search interface and return it.
    """
    if isinstance(in_date, (datetime, date)):
        return in_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Reference: https://cwiki.apache.org/confluence/display/solr/Working+with+Dates

    # ISO-8601 date or NOW
    valid_date_pattern = r'^(?:\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z|NOW)'
    # date arithmetic suffix is allowed
    units = r'(?:YEAR|MONTH|DAY|HOUR|MINUTE|SECOND)'
    valid_date_pattern += r'(?:[-+]\d+{}S?)*'.format(units)
    # dates can be rounded to a unit of time
    # e.g. "NOW/DAY" for dates since 00:00 today
    valid_date_pattern += r'(?:/{}S?)*$'.format(units)
    in_date = in_date.strip()
    if re.match(valid_date_pattern, in_date):
        return in_date

    try:
        return datetime.strptime(in_date, '%Y%m%d').strftime('%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise ValueError('Unsupported date value {}'.format(in_date))


def _format_order_by(order_by):
    if not order_by or not order_by.strip():
        return None
    output = []
    for part in order_by.split(','):
        part = part.strip()
        dir = " asc"
        if part[0] == '+':
            part = part[1:]
        elif part[0] == '-':
            dir = " desc"
            part = part[1:]
        if not part or not part.isalnum():
            raise ValueError("Invalid order by value ({})".format(order_by))
        output.append(part + dir)
    return ",".join(output)


def _parse_gml_footprint(geometry_str):
    geometry_xml = ET.fromstring(geometry_str)
    poly_coords_str = geometry_xml \
        .find('{http://www.opengis.net/gml}outerBoundaryIs') \
        .find('{http://www.opengis.net/gml}LinearRing') \
        .findtext('{http://www.opengis.net/gml}coordinates')
    poly_coords = (coord.split(",")[::-1] for coord in poly_coords_str.split(" "))
    coord_string = ",".join(" ".join(coord) for coord in poly_coords)
    return "POLYGON(({}))".format(coord_string)


def _parse_iso_date(content):
    if '.' in content:
        return datetime.strptime(content, '%Y-%m-%dT%H:%M:%S.%fZ')
    else:
        return datetime.strptime(content, '%Y-%m-%dT%H:%M:%SZ')


def _parse_odata_timestamp(in_date):
    """Convert the timestamp received from OData JSON API to a datetime object.
    """
    timestamp = int(in_date.replace('/Date(', '').replace(')/', ''))
    seconds = timestamp // 1000
    ms = timestamp % 1000
    return datetime.utcfromtimestamp(seconds) + timedelta(milliseconds=ms)


def _parse_opensearch_response(products):
    """Convert a query response to a dictionary.

    The resulting dictionary structure is {<product id>: {<property>: <value>}}.
    The property values are converted to their respective Python types unless `parse_values` is set to `False`.
    """

    converters = {'date': _parse_iso_date, 'int': int, 'long': int, 'float': float, 'double': float}
    # Keep the string type by default
    default_converter = lambda x: x

    output = OrderedDict()
    for prod in products:
        product_dict = {}
        prod_id = prod['id']
        output[prod_id] = product_dict
        for key in prod:
            if key == 'id':
                continue
            if isinstance(prod[key], string_types):
                product_dict[key] = prod[key]
            else:
                properties = prod[key]
                if isinstance(properties, dict):
                    properties = [properties]
                if key == 'link':
                    for p in properties:
                        name = 'link'
                        if 'rel' in p:
                            name = 'link_' + p['rel']
                        product_dict[name] = p['href']
                else:
                    f = converters.get(key, default_converter)
                    for p in properties:
                        try:
                            product_dict[p['name']] = f(p['content'])
                        except KeyError:  # Sentinel-3 has one element 'arr' which violates the name:content convention
                            product_dict[p['name']] = f(p['str'])
    return output


def _parse_odata_response(product):
    output = {
        'id': product['Id'],
        'title': product['Name'],
        'size': int(product['ContentLength']),
        product['Checksum']['Algorithm'].lower(): product['Checksum']['Value'],
        'date': _parse_odata_timestamp(product['ContentDate']['Start']),
        'footprint': _parse_gml_footprint(product["ContentGeometry"]),
        'url': product['__metadata']['media_src']
    }
    # Parse the extended metadata, if provided
    converters = [int, float, _parse_iso_date]
    for attr in product['Attributes'].get('results', []):
        value = attr['Value']
        for f in converters:
            try:
                value = f(attr['Value'])
                break
            except ValueError:
                pass
        output[attr['Name']] = value
    return output


def _md5_compare(file_path, checksum, block_size=2 ** 13):
    """Compare a given md5 checksum with one calculated from a file"""
    with closing(tqdm(desc="MD5 checksumming", total=getsize(file_path), unit="B", unit_scale=True)) as progress:
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                block_data = f.read(block_size)
                if not block_data:
                    break
                md5.update(block_data)
                progress.update(len(block_data))
        return md5.hexdigest().lower() == checksum.lower()


def _download(url, path, session, file_size):
    headers = {}
    continuing = exists(path)
    if continuing:
        headers = {'Range': 'bytes={}-'.format(getsize(path))}
    downloaded_bytes = 0
    with closing(session.get(url, stream=True, auth=session.auth, headers=headers)) as r, \
            closing(tqdm(desc="Downloading", total=file_size, unit="B", unit_scale=True)) as progress:
        _check_scihub_response(r, test_json=False)
        chunk_size = 2 ** 20  # download in 1 MB chunks
        mode = 'ab' if continuing else 'wb'
        with open(path, mode) as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    progress.update(len(chunk))
                    downloaded_bytes += len(chunk)
        # Return the number of bytes downloaded
        return progress.n
