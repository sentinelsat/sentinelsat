# -*- coding: utf-8 -*-
from __future__ import print_function

from homura import download
from pycurl import CAINFO
import requests
import geojson

try:
    import certifi
except ImportError:
    certifi = None

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from time import sleep
try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin
from os.path import join, exists
from os import remove


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
    """

    def __init__(self, user, password, api_url='https://scihub.copernicus.eu/apihub/'):
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.api_url = self._url_trail_slash(api_url)

    def query(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Query the SciHub API with the coordinates of an area, a date inverval
        and any other search keywords accepted by the SciHub API.
        """
        self.format_url(area, initial_date, end_date, **keywords)
        try:
            self.content = requests.post(self.url, dict(q=self.query),
                                         auth=self.session.auth)
            # anything other than 2XX is considered an error
            if not self.content.status_code // 100 == 2:
                print(('Error: API returned unexpected response {} .'.format(self.content.status_code)))
        except requests.exceptions.RequestException as exc:
            print('Error: {}'.format(exc))

    @staticmethod
    def _url_trail_slash(api_url):
        """Add trailing slash to the api url if it is missing"""
        if api_url[-1] is not '/':
            api_url += '/'
        return api_url

    def format_url(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Create the URL to access the SciHub API, defining the max quantity of
        results to 15000 items.
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

        self.url = urljoin(self.api_url, 'search?format=json&rows=15000')
        self.query = ''.join([acquisition_date, query_area, filters])

    def get_products(self):
        """Return the result of the Query in json format."""
        try:
            self.products = self.content.json()['feed']['entry']
            # this verification is necessary because if the query returns only
            # one product, self.products will be a dict not a list
            if type(self.products) == dict:
                return [self.products]
            else:
                return self.products
        except KeyError:
            print('No products found in this query.')
            return []
        except ValueError:  # catch simplejson.decoder.JSONDecodeError
            raise ValueError('API response not valid. JSON decoding failed.')

    def get_products_size(self):
        """Return the total filesize in Gb of all products in the query"""
        size_total = 0
        for product in self.get_products():
            size_product = next(x for x in product["str"] if x["name"] == "size")["content"]
            size_value = float(size_product.split(" ")[0])
            size_unit = str(size_product.split(" ")[1])
            if size_unit == "MB":
                size_value /= 1024
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
            coord_list_split = [coord.split(" ") for coord in coord_list]
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

        product = self.session.get(
            urljoin(self.api_url, "odata/v1/Products('%s')/?$format=json" % id)
        )

        try:
            product_json = product.json()
        except ValueError:
            raise ValueError('Invalid API response. JSON decoding failed.')

        # parse the GML footprint to same format as returned
        # by .get_coordinates()
        geometry_xml = ET.fromstring(product_json["d"]["ContentGeometry"])
        poly_coords = geometry_xml \
            .find('{http://www.opengis.net/gml}outerBoundaryIs') \
            .find('{http://www.opengis.net/gml}LinearRing') \
            .findtext('{http://www.opengis.net/gml}coordinates')
        coord_string = ",".join(
            [" ".join(double_coord) for double_coord in [coord.split(",") for coord in poly_coords.split(" ")]]
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

    def download(self, id, path='.', checksum=False, **kwargs):
        """Download a product using homura's download function.

        If you don't pass the title of the product, it will use the id as
        filename. Further keyword arguments are passed to the
        homura.download() function.
        """
        # Check if API is reachable.
        product = None
        while product is None:
            try:
                product = self.get_product_info(id)
            except ValueError:
                print("Invalid API response. Trying again in 3 minutes.")
                sleep(180)

        path = join(path, product['title'] + '.zip')
        kwargs = self._fillin_cainfo(kwargs)

        print('Downloading %s to %s' % (id, path))

        # Check if the file exists and passes md5 test
        if exists(path):
            if md5_compare(path, product['md5'].lower()):
                print('%s was already downloaded.' % path)
                return path
            else:
                remove(path)

        download(product['url'], path=path, session=self.session, **kwargs)

        # Check integrity with MD5 checksum
        if checksum is True:
            if not md5_compare(path, product['md5'].lower()):
                raise ValueError('File corrupt: Checksums do not match')
        return path

    def download_all(self, path='.', checksum=False, **kwargs):
        """Download all products using homura's download function.

        It will use the products id as filenames. If the checksum calculation
        fails a list with tuples of filename and product ids of the corrupt
        scenes will be returned. Further keyword arguments are passed to the
        homura.download() function.
        """
        corrupt_scenes = []
        for product in self.get_products():
            try:
                self.download(product['id'], path, checksum, **kwargs)
            except ValueError:
                corrupt_scenes.append((product['title'] + '.zip', product['id']))
        return corrupt_scenes

    @staticmethod
    def _fillin_cainfo(kwargs_dict):
        """Fill in the path of the PEM file containing the CA certificate.

        The priority is: 1. user provided path, 2. path to the cacert.pem
        bundle provided by certifi (if installed), 3. let pycurl use the
        system path where libcurl's cacert bundle is assumed to be stored,
        as established at libcurl build time.
        """
        try:
            cainfo = kwargs_dict['pass_through_opts'][CAINFO]
        except KeyError:
            try:
                cainfo = certifi.where()
            except AttributeError:
                cainfo = None

        if cainfo is not None:
            pass_through_opts = kwargs_dict.get('pass_through_opts', {})
            pass_through_opts[CAINFO] = cainfo
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
        string of comma separated coordinate tuples to be used by SentinelAPI
    """
    geojson_obj = geojson.loads(open(geojson_file, 'r').read())
    coordinates = geojson_obj['features'][feature_number]['geometry']['coordinates'][0]
    # precision of 7 decimals equals 1mm at the equator
    coordinates = ['%.7f %.7f' % tuple(coord) for coord in coordinates]
    return ','.join(coordinates)


def md5_compare(file_path, checksum, block_size=2 ** 13):
    """Compare a given md5 checksum with one calculated from a file"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            block_data = f.read(block_size)
            if not block_data:
                break
            md5.update(block_data)
    return md5.hexdigest() == checksum
