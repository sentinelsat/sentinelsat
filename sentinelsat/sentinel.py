# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import sys
import traceback
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from os import remove
from os.path import join, exists, getsize
import pycurl
from time import sleep

import geojson
import homura
import html2text
import requests
from tqdm import tqdm

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

try:
    import certifi
except ImportError:
    certifi = None


class SentinelAPIError(Exception):
    """Invalid responses from SciHub.
    """
    def __init__(self, http_status=None, code=None, msg=None, response_body=None):
        self.http_status = http_status
        self.code = code
        self.msg = msg
        self.response_body = response_body

    def __str__(self):
        return '(HTTP status: {0}, code: {1}) {2}'.format(
            self.http_status, self.code,
            ('\n' if '\n' in self.msg else '') + self.msg)


class InvalidChecksumError(Exception):
    """MD5 checksum of local file does not match the one from the server.
    """
    pass


def format_date(in_date):
    """Format date or datetime input or a YYYYMMDD string input to
    YYYY-MM-DDThh:mm:ssZ string format. In case you pass an
    """

    if type(in_date) == datetime or type(in_date) == date:
        return in_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        try:
            return datetime.strptime(in_date, '%Y%m%d').strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            return in_date


def convert_timestamp(in_date):
    """Convert the timestamp received from Products API, to
    YYYY-MM-DDThh:mm:ssZ string format.
    """
    in_date = int(in_date.replace('/Date(', '').replace(')/', '')) / 1000
    return format_date(datetime.utcfromtimestamp(in_date))


def _check_scihub_response(response):
    """Check that the response from server has status code 2xx and that the response is valid JSON."""
    try:
        response.raise_for_status()
        response.json()
    except (requests.HTTPError, ValueError) as e:
        msg = "API response not valid. JSON decoding failed."
        code = None
        try:
            msg = response.json()['error']['message']['value']
            code = response.json()['error']['code']
        except:
            if not response.text.rstrip().startswith('{'):
                try:
                    h = html2text.HTML2Text()
                    h.ignore_images = True
                    h.ignore_anchors = True
                    msg = h.handle(response.text).strip()
                except:
                    pass
        api_error = SentinelAPIError(response.status_code, code, msg, response.content)
        # Suppress "During handling of the above exception..." message
        # See PEP 409
        api_error.__cause__ = None
        raise api_error


class SentinelAPI(object):
    """Class to connect to Sentinel Data Hub, search and download imagery.

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

    def __init__(self, user, password, api_url='https://scihub.copernicus.eu/apihub/'):
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.api_url = api_url if api_url.endswith('/') else api_url + '/'
        self.url = None
        self.last_query = None
        self.last_status_code = None
        self.content = None
        self.products = []
        self.page_size = 100

    def format_url(self, start_row=0):
        blank = 'search?format=json&rows={rows}&start={start}'.format(
            rows=self.page_size, start=start_row
            )
        self.url = urljoin(self.api_url, blank)
        return self.url

    def query(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Query the SciHub API with the coordinates of an area, a date interval
        and any other search keywords accepted by the SciHub API.
        """
        query = self.format_query(area, initial_date, end_date, **keywords)
        self.load_query(query)
        return self.products

    def load_query(self, query, start_row=0):
        """Do a full-text query on the SciHub API using the format specified in
           https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/3FullTextSearch
        """
        # store last query (for testing)
        self.last_query = query

        # generate URL
        url = self.format_url(start_row=start_row)

        # load query results
        content = requests.post(url, dict(q=query), auth=self.session.auth)
        _check_scihub_response(content)

        # store last status code (for testing)
        self.last_status_code = content.status_code

        # parse content
        total_results = 0
        try:
            json_feed = content.json()['feed']
            products = json_feed['entry']
            # this verification is necessary because if the query returns only
            # one product, self.products will be a dict not a list
            if type(products) == dict:
                products = [products]

            # append to products
            self.products += products

            # get total number of returned results
            total_results = int(json_feed['opensearch:totalResults'])
            if total_results == 0:
                raise KeyError('No results returned.')
        except KeyError:
            print('No products found in this query.')
            return []
        except ValueError:
            raise SentinelAPIError(http_status=content.status_code,
                                   msg='API response not valid. JSON decoding failed.',
                                   response_body=content.content)

        # repeat query until all results have been loaded
        if total_results > self.page_size + start_row - 1:
            self.load_query(query, start_row=(start_row + self.page_size))

    @staticmethod
    def format_query(area, initial_date=None, end_date=datetime.now(), **keywords):
        """Create the SciHub API query string
        """
        if initial_date is None:
            initial_date = end_date - timedelta(hours=24)

        acquisition_date = '(beginPosition:[%s TO %s])' % (
            format_date(initial_date),
            format_date(end_date)
        )
        query_area = ' AND (footprint:"Intersects(POLYGON((%s)))")' % area

        filters = ''
        for kw in sorted(keywords.keys()):
            filters += ' AND (%s:%s)' % (kw, keywords[kw])

        query = ''.join([acquisition_date, query_area, filters])
        return query

    def get_products(self):
        """Return the result of the Query in json format."""
        return self.products

    def get_products_size(self):
        """Return the total filesize in GB of all products in the query"""
        size_total = 0
        for product in self.get_products():
            size_product = next(x for x in product["str"] if x["name"] == "size")["content"]
            size_value = float(size_product.split(" ")[0])
            size_unit = str(size_product.split(" ")[1])
            if size_unit == "MB":
                size_value /= 1024
            if size_unit == "KB":
                size_value /= 1024 * 1024
            size_total += size_value
        return round(size_total, 2)

    def get_footprints(self):
        """Return the footprints of the resulting scenes in GeoJSON format"""
        id = 0
        feature_list = []

        for scene in self.get_products():
            id += 1
            # parse the polygon
            coord_list = next(
                x
                for x in scene["str"]
                if x["name"] == "footprint"
            )["content"][10:-2].split(",")
            coord_list_split = (coord.split(" ") for coord in coord_list)
            poly = geojson.Polygon([[
                tuple((float(coord[0]), float(coord[1])))
                for coord in coord_list_split
                ]])

            # parse the following properties:
            # platformname, identifier, product_id, date, polarisation,
            # sensor operation mode, orbit direction, product type, download link
            props = {
                "product_id": scene["id"],
                "date_beginposition": next(
                    x
                    for x in scene["date"]
                    if x["name"] == "beginposition"
                )["content"],
                "download_link": next(
                    x
                    for x in scene["link"]
                    if len(x.keys()) == 1
                )["href"]
            }
            # Sentinel-2 has no "polarisationmode" property
            try:
                str_properties = ["platformname", "identifier", "polarisationmode",
                                  "sensoroperationalmode", "orbitdirection", "producttype"]
                for str_prop in str_properties:
                    props.update(
                        {str_prop: next(x for x in scene["str"] if x["name"] == str_prop)["content"]}
                    )
            except:
                str_properties = ["platformname", "identifier",
                                  "sensoroperationalmode", "orbitdirection", "producttype"]
                for str_prop in str_properties:
                    props.update(
                        {str_prop: next(x for x in scene["str"] if x["name"] == str_prop)["content"]}
                    )

            feature_list.append(
                geojson.Feature(geometry=poly, id=id, properties=props)
            )
        return geojson.FeatureCollection(feature_list)

    def get_product_info(self, id):
        """Access SciHub API to get info about a Product. Returns a dict
        containing the id, title, size, md5sum, date, footprint and download url
        of the Product. The date field receives the Start ContentDate of the API.
        """

        response = self.session.get(
            urljoin(self.api_url, "odata/v1/Products('%s')/?$format=json" % id)
        )
        _check_scihub_response(response)

        product_json = response.json()

        # parse the GML footprint to same format as returned
        # by .get_coordinates()
        geometry_xml = ET.fromstring(product_json["d"]["ContentGeometry"])
        poly_coords = geometry_xml \
            .find('{http://www.opengis.net/gml}outerBoundaryIs') \
            .find('{http://www.opengis.net/gml}LinearRing') \
            .findtext('{http://www.opengis.net/gml}coordinates')
        coord_string = ",".join(
            [" ".join(double_coord[::-1]) for double_coord in [coord.split(",") for coord in poly_coords.split(" ")]]
        )

        keys = ['id', 'title', 'size', 'md5', 'date', 'footprint', 'url']
        values = [
            product_json['d']['Id'],
            product_json['d']['Name'],
            int(product_json['d']['ContentLength']),
            product_json['d']['Checksum']['Value'],
            convert_timestamp(product_json['d']['ContentDate']['Start']),
            coord_string,
            urljoin(self.api_url, "odata/v1/Products('%s')/$value" % id)
        ]
        return dict(zip(keys, values))

    def download(self, id, directory_path='.', checksum=False, check_existing=False, **kwargs):
        """Download a product using homura.

        Uses the filename on the server for the downloaded file, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.zip".

        Incomplete downloads are continued and complete files are skipped.

        Further keyword arguments are passed to the homura.download() function.

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
        check_existing : bool, optional
            If True and a fully downloaded file with the same name exists on the disk,
            verify its integrity using its MD5 checksum. Re-download in case of non-matching checksums.
            Defaults to False.

        Returns
        -------
        path : string
            Disk path of the downloaded file,
        product_info : dict
            Dictionary containing the product's info from get_product_info().

        Raises
        ------
        InvalidChecksumError
            If the MD5 checksum does not match the checksum on the server.
        """
        # Check if API is reachable.
        product_info = None
        while product_info is None:
            try:
                product_info = self.get_product_info(id)
            except SentinelAPIError as e:
                print("Invalid API response:\n{}\nTrying again in 1 minute.".format(str(e)))
                sleep(60)

        path = join(directory_path, product_info['title'] + '.zip')
        kwargs = self._fillin_cainfo(kwargs)

        print('Downloading %s to %s' % (id, path))

        # Check if the file exists and passes md5 test
        # Homura will by default continue the download if the file exists but is incomplete
        if exists(path) and getsize(path) == product_info['size']:
            if not check_existing or md5_compare(path, product_info['md5']):
                print('%s was already downloaded.' % path)
                return path, product_info
            else:
                print('%s was already downloaded but is corrupt: checksums do not match. Re-downloading.' % path)
                remove(path)

        if (exists(path) and getsize(path) >= 2 ** 31 and
                pycurl.version.split()[0].lower() <= 'pycurl/7.43.0'):
            # Workaround for PycURL's bug when continuing > 2 GB files
            # https://github.com/pycurl/pycurl/issues/405
            remove(path)

        homura.download(product_info['url'], path=path, session=self.session, **kwargs)

        # Check integrity with MD5 checksum
        if checksum is True:
            if not md5_compare(path, product_info['md5']):
                raise InvalidChecksumError('File corrupt: checksums do not match')
        return path, product_info

    def download_all(self, directory_path='.', max_attempts=10, checksum=False, check_existing=False, **kwargs):
        """Download all products returned in query().

        File names on the server are used for the downloaded files, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.zip".

        In case of interruptions or other exceptions, downloading will restart from where it left off.
        Downloading is attempted at most max_attempts times to avoid getting stuck with unrecoverable errors.

        Parameters
        ----------
        directory_path : string
            Directory where the downloaded files will be downloaded
        max_attempts : int, optional
            Number of allowed retries before giving up downloading a product. Defaults to 10.

        Other Parameters
        ----------------
        See download().

        Returns
        -------
        dict[string, dict|None]
            A dictionary with an entry for each product mapping the downloaded file path to its product info
            (returned by get_product_info()). Product info is set to None if downloading the product failed.
        """
        result = {}
        products = self.get_products()
        print("Will download %d products" % len(products))
        for i, product in enumerate(products):
            path = join(directory_path, product['title'] + '.zip')
            product_info = None
            download_successful = False
            remaining_attempts = max_attempts
            while not download_successful and remaining_attempts > 0:
                try:
                    path, product_info = self.download(product['id'], directory_path, checksum, check_existing,
                                                       **kwargs)
                    download_successful = True
                except (KeyboardInterrupt, SystemExit, SystemError, MemoryError):
                    raise
                except InvalidChecksumError:
                    print("Invalid checksum. The downloaded file is corrupted.")
                except:
                    print("There was an error downloading %s" % product['title'], file=sys.stderr)
                    traceback.print_exc()
                remaining_attempts -= 1
            result[path] = product_info
            print("{}/{} products downloaded".format(i + 1, len(products)))
        return result

    @staticmethod
    def _fillin_cainfo(kwargs_dict):
        """Fill in the path of the PEM file containing the CA certificate.

        The priority is: 1. user provided path, 2. path to the cacert.pem
        bundle provided by certifi (if installed), 3. let pycurl use the
        system path where libcurl's cacert bundle is assumed to be stored,
        as established at libcurl build time.
        """
        try:
            cainfo = kwargs_dict['pass_through_opts'][pycurl.CAINFO]
        except KeyError:
            try:
                cainfo = certifi.where()
            except AttributeError:
                cainfo = None

        if cainfo is not None:
            pass_through_opts = kwargs_dict.get('pass_through_opts', {})
            pass_through_opts[pycurl.CAINFO] = cainfo
            kwargs_dict['pass_through_opts'] = pass_through_opts

        return kwargs_dict


def get_coordinates(geojson_file, feature_number=0):
    """Return the coordinates of a polygon of a GeoJSON file.

    Parameters
    ----------
    geojson_file : str
        location of GeoJSON file_path
    feature_number : int
        Feature to extract polygon from (in case of MultiPolygon
        FeatureCollection), defaults to first Feature

    Returns
    -------
    polygon coordinates
        string of comma separated coordinate tuples (lon, lat) to be used by SentinelAPI
    """
    geojson_obj = geojson.loads(open(geojson_file, 'r').read())
    coordinates = geojson_obj['features'][feature_number]['geometry']['coordinates'][0]
    # precision of 7 decimals equals 1mm at the equator
    coordinates = ['%.7f %.7f' % (coord[0], coord[1]) for coord in coordinates]
    return ','.join(coordinates)


def md5_compare(file_path, checksum, block_size=2 ** 13):
    """Compare a given md5 checksum with one calculated from a file"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        progress = tqdm(desc="MD5 checksumming", total=getsize(file_path), unit="B", unit_scale=True)
        while True:
            block_data = f.read(block_size)
            if not block_data:
                break
            md5.update(block_data)
            progress.update(len(block_data))
        progress.close()
    return md5.hexdigest().lower() == checksum.lower()
