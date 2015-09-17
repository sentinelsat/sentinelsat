# -*- coding: utf-8 -*-
from __future__ import print_function

from homura import download
from pycurl import CAINFO
import requests
import json

try:
    import certifi
except ImportError:
    certifi = None

from datetime import datetime, date, timedelta
from os.path import join, exists, getsize


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


class SentinelAPI(object):
    """Class to connect to Sentinel-1 Scientific Data Hub, search and download
    imagery.
    """
    
    def __init__(self, user, password):
        self.session = requests.Session()
        self.session.auth = (user, password)

    def query(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Query the SciHub API with the coordinates of an area, a date inverval
        and any other search keywords accepted by the SciHub API.
        """
        self.format_url(area, initial_date, end_date, **keywords)
        self.content = requests.get(self.url, auth=self.session.auth)
        if self.content.status_code != 200:
            print(('Query returned %s error.' % self.content.status_code))

    def format_url(self, area, initial_date=None, end_date=datetime.now(), **keywords):
        """Create the URL to access the SciHub API, defining the max quantity of
        results to 50 items.
        """
        if initial_date is None:
            initial_date = end_date - timedelta(hours=24)

        ingestion_date = '(ingestionDate:[%s TO %s])' % (
            format_date(initial_date),
            format_date(end_date)
        )
        query_area = ' AND (footprint:"Intersects(POLYGON((%s)))")' % area

        filters = ''
        for kw in sorted(keywords.keys()):
            filters += ' AND (%s:%s)' % (kw, keywords[kw])

        self.url = 'https://scihub.esa.int/dhus/search?format=json&rows=50&q=%s%s%s' \
            % (ingestion_date, query_area, filters)

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

    def get_product_info(self, id):
        """Access SciHub API to get info about a Product. Returns a dict
        containing the id, title, size and download url of the Product.
        """

        product = self.session.get(
            "https://scihub.esa.int/dhus/odata/v1/Products('%s')/?$format=json" % id
            )
        product_json = product.json()
        keys = ['id', 'title', 'size', 'url']
        values = [
            product_json['d']['Id'],
            product_json['d']['Name'],
            int(product_json['d']['ContentLength']),
            "https://scihub.esa.int/dhus/odata/v1/Products('%s')/$value" % id
            ]
        return dict(zip(keys, values))

    def download(self, id, path='.', **kwargs):
        """Download a product using homura's download function. If you don't
        pass the title of the product, it will use the id as filename. Further
        keyword arguments are passed to homura.
        """
        product = self.get_product_info(id)
        path = join(path, product['title'] + '.zip')
        kwargs = self._fillin_cainfo(kwargs)

        print('Downloading %s to %s' % (id, path))

        # Check if the file exists and if it is complete
        if exists(path):
            if getsize(path) == product['size']:
                print('%s was already downloaded.' % path)
                return path
        
        download(product['url'], path=path, session=self.session, **kwargs)
        return path

    def download_all(self, path='.', **kwargs):
        for product in self.get_products():
            self.download(product['id'], path, **kwargs)

    @staticmethod
    def _fillin_cainfo(kwargs_dict):
        """Pick the path of the PEM file containing the CA certificate.
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
        
        if cainfo != None:
            pass_through_opts = kwargs_dict.get('pass_through_opts', {})
            pass_through_opts[CAINFO] = cainfo
            kwargs_dict['pass_through_opts'] = pass_through_opts
        
        return kwargs_dict


def get_coordinates(geojson_file, feature_number=0):
    """Return the coordinates of a polygon of a GeoJSON file."""
    geojson = json.loads(open(geojson_file, 'r').read())
    coordinates = geojson['features'][feature_number]['geometry']['coordinates'][0]
    coordinates = ['%s %s' % tuple(coord) for coord in coordinates]
    return ','.join(coordinates)
