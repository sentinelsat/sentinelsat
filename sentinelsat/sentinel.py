import concurrent.futures
import hashlib
import itertools
import logging
import re
import shutil
import threading
import warnings
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict, namedtuple
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote_plus, urljoin

import geojson
import geomet.wkt
import html2text
import requests
from tqdm.auto import tqdm

from sentinelsat.exceptions import (
    InvalidChecksumError,
    InvalidKeyError,
    LTAError,
    LTATriggered,
    QueryLengthError,
    QuerySyntaxError,
    SentinelAPIError,
    ServerError,
    UnauthorizedError,
)
from . import __version__ as sentinelsat_version


class SentinelAPI:
    """Class to connect to Copernicus Open Access Hub, search and download imagery.

    Parameters
    ----------
    user : string
        username for DataHub
        set to None to use ~/.netrc
    password : string
        password for DataHub
        set to None to use ~/.netrc
    api_url : string, optional
        URL of the DataHub
        defaults to 'https://apihub.copernicus.eu/apihub'
    show_progressbars : bool
        Whether progressbars should be shown or not, e.g. during download. Defaults to True.
    timeout : float or tuple, default 60
        How long to wait for DataHub response (in seconds).
        Tuple (connect, read) allowed.
        Set to None to wait indefinitely.

    Attributes
    ----------
    session : requests.Session
        Session to connect to DataHub
    api_url : str
        URL to the DataHub
    page_size : int
        Number of results per query page.
        Current value: 100 (maximum allowed on ApiHub)
    timeout : float or tuple
        How long to wait for DataHub response (in seconds).
    """

    logger = logging.getLogger("sentinelsat.SentinelAPI")

    def __init__(
        self,
        user,
        password,
        api_url="https://apihub.copernicus.eu/apihub/",
        show_progressbars=True,
        timeout=60,
    ):
        self.session = requests.Session()
        if user and password:
            self.session.auth = (user, password)
        self.api_url = api_url if api_url.endswith("/") else api_url + "/"
        self.page_size = 100
        self.user_agent = "sentinelsat/" + sentinelsat_version
        self.session.headers["User-Agent"] = self.user_agent
        self.session.timeout = timeout
        self.show_progressbars = show_progressbars
        self._dhus_version = None
        # For unit tests
        self._last_query = None
        self._last_response = None

    @staticmethod
    def _api2dhus_url(api_url):
        url = re.sub("apihub/$", "dhus/", api_url)
        url = re.sub("apihub.copernicus.eu", "scihub.copernicus.eu", url)
        return url

    def _req_dhus_stub(self):
        try:
            resp = self.session.get(self.api_url + "api/stub/version")
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.logger.error("HTTPError: %s", err)
            self.logger.error("Are you trying to get the DHuS version of APIHub?")
            self.logger.error("Trying again after conversion to DHuS URL")
            resp = self.session.get(self._api2dhus_url(self.api_url) + "api/stub/version")
            resp.raise_for_status()
        return resp.json()["value"]

    @property
    def dhus_version(self):
        if self._dhus_version is None:
            self._dhus_version = self._req_dhus_stub()
        return self._dhus_version

    def query(
        self,
        area=None,
        date=None,
        raw=None,
        area_relation="Intersects",
        order_by=None,
        limit=None,
        offset=0,
        **keywords
    ):
        """Query the OpenSearch API with the coordinates of an area, a date interval
        and any other search keywords accepted by the API.

        Parameters
        ----------
        area : str, optional
            The area of interest formatted as a Well-Known Text string.
        date : tuple of (str or datetime) or str, optional
            A time interval filter based on the Sensing Start Time of the products.
            Expects a tuple of (start, end), e.g. ("NOW-1DAY", "NOW").
            The timestamps can be either a Python datetime or a string in one of the
            following formats:

                - yyyyMMdd
                - yyyy-MM-ddThh:mm:ss.SSSZ (ISO-8601)
                - yyyy-MM-ddThh:mm:ssZ
                - NOW
                - NOW-<n>DAY(S) (or HOUR(S), MONTH(S), etc.)
                - NOW+<n>DAY(S)
                - yyyy-MM-ddThh:mm:ssZ-<n>DAY(S)
                - NOW/DAY (or HOUR, MONTH etc.) - rounds the value to the given unit

            Alternatively, an already fully formatted string such as "[NOW-1DAY TO NOW]" can be
            used as well.
        raw : str, optional
            Additional query text that will be appended to the query.
        area_relation : {'Intersects', 'Contains', 'IsWithin'}, optional
            What relation to use for testing the AOI. Case insensitive.

                - Intersects: true if the AOI and the footprint intersect (default)
                - Contains: true if the AOI is inside the footprint
                - IsWithin: true if the footprint is inside the AOI

        order_by: str, optional
            A comma-separated list of fields to order by (on server side).
            Prefix the field name by '+' or '-' to sort in ascending or descending order,
            respectively. Ascending order is used if prefix is omitted.
            Example: "cloudcoverpercentage, -beginposition".
        limit: int, optional
            Maximum number of products returned. Defaults to no limit.
        offset: int, optional
            The number of results to skip. Defaults to 0.
        **keywords
            Additional keywords can be used to specify other query parameters,
            e.g. `relativeorbitnumber=70`.
            See https://scihub.copernicus.eu/twiki/do/view/SciHubUserGuide/3FullTextSearch
            for a full list.


        Range values can be passed as two-element tuples, e.g. `cloudcoverpercentage=(0, 30)`.
        `None` can be used in range values for one-sided ranges, e.g. `orbitnumber=(16302, None)`.
        Ranges with no bounds (`orbitnumber=(None, None)`) will not be included in the query.

        Multiple values for the same query parameter can be provided as sets and will be handled as
        logical OR, e.g. `orbitnumber={16302, 1206}`.

        The time interval formats accepted by the `date` parameter can also be used with
        any other parameters that expect time intervals (that is: 'beginposition', 'endposition',
        'date', 'creationdate', and 'ingestiondate').

        Returns
        -------
        dict[string, dict]
            Products returned by the query as a dictionary with the product ID as the key and
            the product's attributes (a dictionary) as the value.
        """
        query = self.format_query(area, date, raw, area_relation, **keywords)

        if query.strip() == "":
            # An empty query should return the full set of products on the server, which is a bit unreasonable.
            # The server actually raises an error instead and it's better to fail early in the client.
            raise ValueError("Empty query.")

        # check query length - often caused by complex polygons
        if self.check_query_length(query) > 1.0:
            self.logger.warning(
                "The query string is too long and will likely cause a bad DHuS response."
            )

        self.logger.debug(
            "Running query: order_by=%s, limit=%s, offset=%s, query=%s",
            order_by,
            limit,
            offset,
            query,
        )
        formatted_order_by = _format_order_by(order_by)
        response, count = self._load_query(query, formatted_order_by, limit, offset)
        self.logger.info("Found %s products", count)
        return _parse_opensearch_response(response)

    @staticmethod
    def format_query(area=None, date=None, raw=None, area_relation="Intersects", **keywords):
        """Create a OpenSearch API query string."""
        if area_relation.lower() not in {"intersects", "contains", "iswithin"}:
            raise ValueError("Incorrect AOI relation provided ({})".format(area_relation))

        # Check for duplicate keywords
        kw_lower = {x.lower() for x in keywords}
        if (
            len(kw_lower) != len(keywords)
            or (date is not None and "beginposition" in kw_lower)
            or (area is not None and "footprint" in kw_lower)
        ):
            raise ValueError(
                "Query contains duplicate keywords. Note that query keywords are case-insensitive."
            )

        query_parts = []

        if date is not None:
            keywords["beginPosition"] = date

        for attr, value in sorted(keywords.items()):
            if isinstance(value, set):
                if len(value) == 0:
                    continue
                sub_parts = []
                for sub_value in value:
                    sub_value = _format_query_value(attr, sub_value)
                    if sub_value is not None:
                        sub_parts.append(f"{attr}:{sub_value}")
                sub_parts = sorted(sub_parts)
                query_parts.append("({})".format(" OR ".join(sub_parts)))
            else:
                value = _format_query_value(attr, value)
                if value is not None:
                    query_parts.append(f"{attr}:{value}")

        if raw:
            query_parts.append(raw)

        if area is not None:
            query_parts.append('footprint:"{}({})"'.format(area_relation, area))

        return " ".join(query_parts)

    def count(self, area=None, date=None, raw=None, area_relation="Intersects", **keywords):
        """Get the number of products matching a query.

        Accepted parameters are identical to :meth:`SentinelAPI.query()`.

        This is a significantly more efficient alternative to doing `len(api.query())`,
        which can take minutes to run for queries matching thousands of products.

        Returns
        -------
        int
            The number of products matching a query.
        """
        for kw in ["order_by", "limit", "offset"]:
            # Allow these function arguments to be included for compatibility with query(),
            # but ignore them.
            if kw in keywords:
                del keywords[kw]
        query = self.format_query(area, date, raw, area_relation, **keywords)
        _, total_count = self._load_query(query, limit=0)
        return total_count

    def _load_query(self, query, order_by=None, limit=None, offset=0):
        products, count = self._load_subquery(query, order_by, limit, offset)

        # repeat query until all results have been loaded
        max_offset = count
        if limit is not None:
            max_offset = min(count, offset + limit)
        if max_offset > offset + self.page_size:
            progress = self._tqdm(
                desc="Querying products",
                initial=self.page_size,
                total=max_offset - offset,
                unit=" products",
            )
            for new_offset in range(offset + self.page_size, max_offset, self.page_size):
                new_limit = limit
                if limit is not None:
                    new_limit = limit - new_offset + offset
                ret = self._load_subquery(query, order_by, new_limit, new_offset)[0]
                progress.update(len(ret))
                products += ret
            progress.close()

        return products, count

    def _load_subquery(self, query, order_by=None, limit=None, offset=0):
        # store last query (for testing)
        self._last_query = query
        self.logger.debug("Sub-query: offset=%s, limit=%s", offset, limit)

        # load query results
        url = self._format_url(order_by, limit, offset)
        # Unlike POST, DHuS only accepts latin1 charset in the GET params
        response = self.session.get(url, params={"q": query.encode("latin1")})
        _check_scihub_response(response, query_string=query)

        # store last status code (for testing)
        self._last_response = response

        # parse response content
        try:
            json_feed = response.json()["feed"]
            if "error" in json_feed:
                message = json_feed["error"]["message"]
                message = message.replace("org.apache.solr.search.SyntaxError: ", "")
                raise QuerySyntaxError(message, response)
            total_results = int(json_feed["opensearch:totalResults"])
        except (ValueError, KeyError):
            raise ServerError("API response not valid. JSON decoding failed.", response)

        products = json_feed.get("entry", [])
        # this verification is necessary because if the query returns only
        # one product, self.products will be a dict not a list
        if isinstance(products, dict):
            products = [products]

        return products, total_results

    def _format_url(self, order_by=None, limit=None, offset=0):
        if limit is None:
            limit = self.page_size
        limit = min(limit, self.page_size)
        url = "search?format=json&rows={}".format(limit)
        url += "&start={}".format(offset)
        if order_by:
            url += "&orderby={}".format(order_by)
        return urljoin(self.api_url, url)

    @staticmethod
    def to_geojson(products):
        """Return the products from a query response as a GeoJSON with the values in their
        appropriate Python types.
        """
        feature_list = []
        for i, (product_id, props) in enumerate(products.items()):
            props = props.copy()
            props["id"] = product_id
            poly = geomet.wkt.loads(props["footprint"])
            del props["footprint"]
            del props["gmlfootprint"]
            # Fix "'datetime' is not JSON serializable"
            for k, v in props.items():
                if isinstance(v, (date, datetime)):
                    props[k] = v.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            feature_list.append(geojson.Feature(geometry=poly, id=i, properties=props))
        return geojson.FeatureCollection(feature_list)

    @staticmethod
    def to_dataframe(products):
        """Return the products from a query response as a Pandas DataFrame
        with the values in their appropriate Python types.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("to_dataframe requires the optional dependency Pandas.")

        return pd.DataFrame.from_dict(products, orient="index")

    @staticmethod
    def to_geodataframe(products):
        """Return the products from a query response as a GeoPandas GeoDataFrame
        with the values in their appropriate Python types.
        """
        try:
            import geopandas as gpd
            import shapely.wkt
        except ImportError:
            raise ImportError(
                "to_geodataframe requires the optional dependencies GeoPandas and Shapely."
            )

        crs = "EPSG:4326"  # WGS84
        if len(products) == 0:
            return gpd.GeoDataFrame(crs=crs, geometry=[])

        df = SentinelAPI.to_dataframe(products)
        geometry = [shapely.wkt.loads(fp) for fp in df["footprint"]]
        # remove useless columns
        df.drop(["footprint", "gmlfootprint"], axis=1, inplace=True)
        return gpd.GeoDataFrame(df, crs=crs, geometry=geometry)

    def get_product_odata(self, id, full=False):
        """Access OData API to get info about a product.

        Returns a dict containing the id, title, size, md5sum, date, footprint and download url
        of the product. The date field corresponds to the Start ContentDate value.

        If `full` is set to True, then the full, detailed metadata of the product is returned
        in addition to the above.

        Parameters
        ----------
        id : string
            The UUID of the product to query
        full : bool
            Whether to get the full metadata for the Product. False by default.

        Returns
        -------
        dict[str, Any]
            A dictionary with an item for each metadata attribute

        Notes
        -----
        For a full list of mappings between the OpenSearch (Solr) and OData attribute names
        see the following definition files:
        https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-1/src/main/resources/META-INF/sentinel-1.owl
        https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-2/src/main/resources/META-INF/sentinel-2.owl
        https://github.com/SentinelDataHub/DataHubSystem/blob/master/addon/sentinel-3/src/main/resources/META-INF/sentinel-3.owl
        """
        url = self._get_odata_url(id, "?$format=json")
        if full:
            url += "&$expand=Attributes"
        response = self.session.get(url)
        _check_scihub_response(response)
        values = _parse_odata_response(response.json()["d"])
        values["quicklook_url"] = self._get_odata_url(id, "/Products('Quicklook')/$value")
        return values

    def is_online(self, id):
        """Returns whether a product is online

        Parameters
        ----------
        id : string
            UUID of the product, e.g. 'a8dd0cfd-613e-45ce-868c-d79177b916ed'

        Returns
        -------
        bool
            True if online, False if in LTA

        See Also
        --------
        ``SentinelAPI.trigger_offline_retrieval()``
        """
        # Check https://scihub.copernicus.eu/userguide/ODataAPI#Products_entity for more information

        url = self._get_odata_url(id, "/Online/$value")
        r = self.session.get(url)
        _check_scihub_response(r)
        return r.json()

    def download(self, id, directory_path=".", checksum=True, **kwargs):
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
            Defaults to True.

        Returns
        -------
        product_info : dict
            Dictionary containing the product's info from get_product_info() as well as
            the path on disk.

        Raises
        ------
        InvalidChecksumError
            If the MD5 checksum does not match the checksum on the server.
        LTATriggered
            If the product has been archived and its retrieval was successfully triggered.
        LTAError
            If the product has been archived and its retrieval failed.

        .. versionchanged:: 1.0.0
           * Added ``**kwargs`` parameter to allow easier specialization of the :class:`SentinelAPI` class.
           * Now raises LTATriggered or LTAError if the product has been archived.
        """
        product_info = self.get_product_odata(id)
        filename = self._get_filename(product_info)
        path = Path(directory_path) / filename
        product_info["path"] = str(path)
        product_info["downloaded_bytes"] = 0

        self.logger.info("Downloading %s to %s", id, path)

        if path.exists():
            # We assume that the product has been downloaded and is complete
            return product_info

        # An incomplete download triggers the retrieval from the LTA if the product is not online
        is_online = not self.trigger_offline_retrieval(id)
        if not is_online:
            raise LTATriggered(id)

        self._download_outer(product_info, path, checksum)
        return product_info

    def _download_outer(self, product_info: Dict[str, Any], path: Path, verify_checksum: bool):
        # Use a temporary file for downloading
        temp_path = path.with_name(path.name + ".incomplete")
        skip_download = False
        if temp_path.exists():
            size = temp_path.stat().st_size
            if size > product_info["size"]:
                self.logger.warning(
                    "Existing incomplete file %s is larger than the expected final size"
                    " (%s vs %s bytes). Deleting it.",
                    str(temp_path),
                    size,
                    product_info["size"],
                )
                temp_path.unlink()
            elif size == product_info["size"]:
                if verify_checksum and not self._md5_compare(temp_path, product_info["md5"]):
                    # Log a warning since this should never happen
                    self.logger.warning(
                        "Existing incomplete file %s appears to be fully downloaded but "
                        "its checksum is incorrect. Deleting it.",
                        str(temp_path),
                    )
                    temp_path.unlink()
                else:
                    skip_download = True
            else:
                # continue downloading
                self.logger.info(
                    "Download will resume from existing incomplete file %s.", temp_path
                )
                pass
        if not skip_download:
            # Store the number of downloaded bytes for unit tests
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            product_info["downloaded_bytes"] = self._download(
                product_info["url"], temp_path, product_info["size"]
            )
        # Check integrity with MD5 checksum
        if verify_checksum is True:
            if not self._md5_compare(temp_path, product_info["md5"]):
                temp_path.unlink()
                raise InvalidChecksumError("File corrupt: checksums do not match")
        # Download successful, rename the temporary file to its proper name
        shutil.move(temp_path, path)

    def _get_filename(self, product_info):
        if not product_info["Online"]:
            req = self.session.get(
                product_info["url"].replace("$value", "Attributes('Filename')/Value/$value")
            )
            _check_scihub_response(req, test_json=False)
            filename = req.text
            # This should cover all currently existing file types: .SAFE, .SEN3, .nc and .EOF
            filename = filename.replace(".SAFE", ".zip")
            filename = filename.replace(".SEN3", ".zip")
            return filename
        req = self.session.head(product_info["url"])
        _check_scihub_response(req, test_json=False)
        cd = req.headers.get("Content-Disposition")
        filename = cd.split("=", 1)[1].strip('"')
        return filename

    def trigger_offline_retrieval(self, uuid):
        """Triggers retrieval of an offline product.

        Trying to download an offline product triggers its retrieval from the long term archive.

        Parameters
        ----------
        uuid : string
            UUID of the product

        Returns
        -------
        bool
            True, if the product retrieval was successfully triggered.
            False, if the product is already online.

        Raises
        ------
        LTAError
            If the request was not accepted due to exceeded user quota or server overload.
        ServerError
            If an unexpected response was received from server.
        UnauthorizedError
            If the provided credentials were invalid.

        Notes
        -----
        https://scihub.copernicus.eu/userguide/LongTermArchive
        """
        r = self.session.head(self._get_download_url(uuid))
        cause = r.headers.get("cause-message")
        # check https://scihub.copernicus.eu/userguide/LongTermArchive#HTTP_Status_codes
        if r.status_code == 200:
            self.logger.debug("Product is online")
            return False
        elif r.status_code == 202:
            self.logger.debug("Accepted for retrieval")
            return True
        elif r.status_code == 403:
            msg = f"User quota exceeded: {cause}"
            self.logger.error(msg)
            raise LTAError(msg, r)
        elif r.status_code == 503:
            msg = f"Request not accepted: {cause}"
            self.logger.error(msg)
            raise LTAError(msg, r)
        elif r.status_code < 400:
            msg = f"Unexpected response {r.status_code}: {cause}"
            self.logger.error(msg)
            raise ServerError(msg, r)
        _check_scihub_response(r, test_json=False)

    def download_all(
        self,
        products,
        directory_path=".",
        max_attempts=10,
        checksum=True,
        n_concurrent_dl=2,
        lta_retry_delay=600,
        **kwargs
    ):
        """Download a list of products.

        Takes a list of product IDs as input. This means that the return value of query() can be
        passed directly to this method.

        File names on the server are used for the downloaded files, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.zip".

        In case of interruptions or other exceptions, downloading will restart from where it left
        off. Downloading is attempted at most max_attempts times to avoid getting stuck with
        unrecoverable errors.

        Parameters
        ----------
        products : list
            List of product IDs
        directory_path : string
            Directory where the downloaded files will be downloaded
        max_attempts : int, optional
            Number of allowed retries before giving up downloading a product. Defaults to 10.
        checksum : bool, optional
            If True, verify the downloaded files' integrity by checking its MD5 checksum.
            Throws InvalidChecksumError if the checksum does not match.
            Defaults to True.
        n_concurrent_dl : integer
            number of concurrent downloads
        lta_retry_delay : integer
            how long to wait between requests to the long term archive. Default is 600 seconds.
        **kwargs :
            additional parameters for the *download* method

        Raises
        ------
        Raises the most recent downloading exception if all downloads failed.

        Returns
        -------
        dict[string, dict]
            A dictionary containing the return value from download() for each successfully
            downloaded product.
        dict[string, dict]
            A dictionary containing the product information for products successfully
            triggered for retrieval from the long term archive but not downloaded.
        dict[string, dict]
            A dictionary containing the product information of products where either
            downloading or triggering failed. "exception" field with the exception info
            is included to the product info dict.


        .. versionchanged:: 0.15
           Added ``**kwargs`` parameter to allow easier specialization of the :class:`SentinelAPI` class.
        """

        product_ids = list(products)
        self.logger.info(
            "Will download %d products using %d workers", len(product_ids), n_concurrent_dl
        )

        product_infos = {}
        online_prods = {}
        offline_prods = {}
        for pid in self._tqdm(
            iterable=product_ids, desc="Fetching archival status", unit=" products"
        ):
            info = self.get_product_odata(pid)
            product_infos[pid] = info
            is_online = not self.trigger_offline_retrieval(pid)
            if is_online:
                online_prods[pid] = info
            else:
                offline_prods[pid] = info

        # Skip already downloaded files.
        # Although the download method also checks, we do not need to retrieve such
        # products from the LTA and use up our quota.
        downloaded_prods = {}
        for product_info in list(offline_prods.values()):
            filename = self._get_filename(product_info)
            path = Path(directory_path) / filename
            if path.exists():
                product_info["path"] = str(path)
                downloaded_prods[product_info["id"]] = product_info
                del offline_prods[product_info["id"]]
            else:
                self.logger.info("Product %s is in LTA.", product_info["id"])

        dl_tasks = {}
        retrieval_scheduled = {}

        # Two separate threadpools for downloading and triggering retrieval.
        # Otherwise triggering might take up all threads and nothing is downloaded.
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_concurrent_dl) as dl_exec:
            # First all online products are downloaded. Subsequently, offline products that might
            # have become available in the meantime are requested.
            for product_info in itertools.chain(online_prods.values(), offline_prods.values()):
                dl_tasks[product_info["id"]] = dl_exec.submit(
                    self._download_online_retry,
                    product_info,
                    directory_path,
                    checksum,
                    max_attempts=max_attempts,
                    **kwargs
                )

            stop_event = threading.Event()
            trigger_thread = threading.Thread(
                target=self._trigger_offline_retrieval_until_stop,
                args=(offline_prods, stop_event, retrieval_scheduled, lta_retry_delay),
            )

            # launch in separate thread so that the as_completed loop is entered
            trigger_thread.start()

            for dl_task in concurrent.futures.as_completed(dl_tasks.values()):
                if not dl_task.cancelled() and not dl_task.exception():
                    product_info = dl_task.result()
                    if product_info is not None:
                        downloaded_prods[product_info["id"]] = product_info
                    # This else catches the first dl_task that did not complete because
                    # the product was not online and _download_online_retry returned None
                    else:
                        stop_event.set()
                        for task in dl_tasks.values():
                            task.cancel()

            # Wait for trigger_thread to finish. This could still place a product on the
            # retrieval_scheduled queue.
            trigger_thread.join()

        retrieval_scheduled = {
            pid: info
            for pid, info in retrieval_scheduled.items()
            if pid not in downloaded_prods.keys()
        }

        failed_prods = {}
        for pid, info in product_infos.items():
            if pid not in downloaded_prods and pid not in retrieval_scheduled:
                if dl_tasks[pid].cancelled():
                    info["exception"] = concurrent.futures.CancelledError()
                else:
                    info["exception"] = dl_tasks[pid].exception()
                failed_prods[pid] = info

        if len(failed_prods) == len(product_ids) and len(product_ids) > 0:
            exception = list(failed_prods.values())[0]["exception"]
            if exception is None:
                raise SentinelAPIError("Downloading all products failed for unknown reason")
            raise exception

        ResultTuple = namedtuple("ResultTuple", ["downloaded", "retrieval_triggered", "failed"])
        return ResultTuple(downloaded_prods, retrieval_scheduled, failed_prods)

    def _trigger_offline_retrieval_until_stop(
        self, product_infos, stop_event, retrieval_scheduled, retry_delay=600
    ):
        """Countinuously triggers retrieval of offline products

        This function is supposed to be called in a separate thread. By setting stop_event it can be stopped.

        Parameters
        ----------
        product_infos : dictionary
            Contains uuid of offline products as keys and their product information as values.
        stop_event: threading.Event
            If this event is set from another thread triggering from the LTA will stop
        retrieval_scheduled: dictionary
            Stores product information of triggered products. This can be accessed by other threads.
        retry_delay: integer
            After an unsuccessful triggering operation. Try again after this delay

        Notes
        -----
        https://scihub.copernicus.eu/userguide/LongTermArchive

        """

        for product_info in product_infos.values():
            while not stop_event.is_set():
                try:
                    triggered = self.trigger_offline_retrieval(product_info["id"])
                    if triggered:
                        self.logger.info("%s accepted for retrieval", product_info["id"])
                        retrieval_scheduled[product_info["id"]] = product_info
                        break
                except LTAError as e:
                    self.logger.info(
                        "Request for %s was not accepted: %s. Retrying in %d seconds",
                        product_info["id"],
                        e.msg,
                        retry_delay,
                    )
                    stop_event.wait(timeout=retry_delay)

    def _download_online_retry(
        self, product_info, directory_path=".", checksum=True, max_attempts=10, **kwargs
    ):
        """Thin wrapper around download with retrying and checking whether a product is online

        Parameters
        ----------

        product_info : dict
            Contains the product's info as returned by get_product_info()
        directory_path : string, optional
            Where the file will be downloaded
        checksum : bool, optional
            If True, verify the downloaded file's integrity by checking its MD5 checksum.
            Throws InvalidChecksumError if the checksum does not match.
            Defaults to True.
        max_attempts : int, optional
            Number of allowed retries before giving up downloading a product. Defaults to 10.

        Returns
        -------
        dict or None:
            Either dictionary containing the product's info or if the product is not online just None

        """
        if max_attempts <= 0:
            return

        id = product_info["id"]
        title = product_info["title"]
        is_online = not self.trigger_offline_retrieval(id)
        if not is_online:
            self.logger.info("%s is not online.", id)
            return

        self.logger.info("%s is online. Starting download", id)
        last_exception = None
        for cnt in range(max_attempts):
            try:
                return self.download(id, directory_path, checksum, **kwargs)
            except Exception as e:
                if isinstance(e, InvalidChecksumError):
                    self.logger.warning(
                        "Invalid checksum. The downloaded file for '%s' is corrupted.",
                        title,
                    )
                else:
                    self.logger.exception("There was an error downloading %s", title)
                self.logger.info("%d retries left", max_attempts - cnt - 1)
                last_exception = e
        self.logger.info("No retries left for %s. Terminating.", title)
        raise last_exception

    def download_all_quicklooks(self, products, directory_path=".", n_concurrent_dl=2):
        """Download quicklook for a list of products.

        Takes a dict of product IDs: product data as input. This means that the return value of
        query() can be passed directly to this method.

        File names on the server are used for the downloaded images, e.g.
        "S2A_MSIL1C_20200924T104031_N0209_R008_T35WMV_20200926T135405.jpeg".

        Parameters
        ----------
        products : dict
            Dict of product IDs, product data
        directory_path : string
            Directory where the downloaded images will be downloaded
        n_concurrent_dl : integer
            Number of concurrent downloads

        Returns
        -------
        dict[string, dict]
            A dictionary containing the return value from download_quicklook() for each
            successfully downloaded quicklook
        dict[string, dict]
            A dictionary containing the error of products where either
            quicklook was not available or it had an unexpected content type
        """

        self.logger.info("Will download %d quicklooks", len(products))

        downloaded_quicklooks = {}
        failed_quicklooks = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=n_concurrent_dl) as dl_exec:
            dl_tasks = {}
            for pid in products:
                future = dl_exec.submit(self.download_quicklook, pid, directory_path)
                dl_tasks[future] = pid

            completed_tasks = concurrent.futures.as_completed(dl_tasks)

            for future in completed_tasks:
                product_info = future.result()
                if product_info["error"] == "":
                    downloaded_quicklooks[dl_tasks[future]] = product_info
                else:
                    failed_quicklooks[dl_tasks[future]] = product_info["error"]

        ResultTuple = namedtuple("ResultTuple", ["downloaded", "failed"])
        return ResultTuple(downloaded_quicklooks, failed_quicklooks)

    def download_quicklook(self, id, directory_path="."):
        """Download a quicklook for a product.

        Uses the filename on the server for the downloaded image, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.jpeg".

        Complete images are skipped.

        Parameters
        ----------
        id : string
            UUID of the product, e.g. 'a8dd0cfd-613e-45ce-868c-d79177b916ed'
        directory_path : string, optional
            Where the image will be downloaded

        Returns
        -------
        quicklook_info : dict
            Dictionary containing the quicklooks's response headers as well as the path on disk.
        """
        product_info = self.get_product_odata(id)
        url = product_info["quicklook_url"]

        path = Path(directory_path) / "{}.jpeg".format(product_info["title"])
        product_info["path"] = str(path)
        product_info["downloaded_bytes"] = 0
        product_info["error"] = ""

        self.logger.info("Downloading quicklook %s to %s", product_info["title"], path)

        r = self.session.get(url)
        _check_scihub_response(r, test_json=False)

        product_info["quicklook_size"] = len(r.content)

        if path.exists():
            return product_info

        content_type = r.headers["content-type"]
        if content_type != "image/jpeg":
            product_info["error"] = "Quicklook is not jpeg but {}".format(content_type)

        if product_info["error"] == "":
            with open(path, "wb") as fp:
                fp.write(r.content)
                product_info["downloaded_bytes"] = len(r.content)

        return product_info

    @staticmethod
    def get_products_size(products):
        """Return the total file size in GB of all products in the OpenSearch response."""
        size_total = 0
        for title, props in products.items():
            size_product = props["size"]
            size_value = float(size_product.split(" ")[0])
            size_unit = str(size_product.split(" ")[1])
            if size_unit == "MB":
                size_value /= 1024.0
            if size_unit == "KB":
                size_value /= 1024.0 * 1024.0
            size_total += size_value
        return round(size_total, 2)

    @staticmethod
    def check_query_length(query):
        """Determine whether a query to the OpenSearch API is too long.

        The length of a query string is limited to approximately 3898 characters but
        any special characters (that is, not alphanumeric or -_.*) will take up more space.

        Parameters
        ----------
        query : str
            The query string

        Returns
        -------
        float
            Ratio of the query length to the maximum length
        """
        # The server uses the Java's URLEncoder implementation internally, which we are replicating here
        effective_length = len(quote_plus(query, safe="-_.*").replace("~", "%7E"))

        return effective_length / 3898

    def _query_names(self, names):
        """Find products by their names, e.g.
        S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.

        Note that duplicates exist on server, so multiple products can be returned for each name.

        Parameters
        ----------
        names : list[string]
            List of product names.

        Returns
        -------
        dict[string, dict[str, dict]]
            A dictionary mapping each name to a dictionary which contains the products with
            that name (with ID as the key).
        """
        products = {}
        for name in names:
            products.update(self.query(identifier=name))

        # Group the products
        output = OrderedDict((name, dict()) for name in names)
        for id, metadata in products.items():
            name = metadata["identifier"]
            output[name][id] = metadata

        return output

    def check_files(self, paths=None, ids=None, directory=None, delete=False):
        """Verify the integrity of product files on disk.

        Integrity is checked by comparing the size and checksum of the file with the respective
        values on the server.

        The input can be a list of products to check or a list of IDs and a directory.

        In cases where multiple products with different IDs exist on the server for given product
        name, the file is considered to be correct if any of them matches the file size and
        checksum. A warning is logged in such situations.

        The corrupt products' OData info is included in the return value to make it easier to
        re-download the products, if necessary.

        Parameters
        ----------
        paths : list[string]
            List of product file paths.
        ids : list[string]
            List of product IDs.
        directory : string
            Directory where the files are located, if checking based on product IDs.
        delete : bool
            Whether to delete corrupt products. Defaults to False.

        Returns
        -------
        dict[str, list[dict]]
            A dictionary listing the invalid or missing files. The dictionary maps the corrupt
            file paths to a list of OData dictionaries of matching products on the server (as
            returned by :meth:`SentinelAPI.get_product_odata()`).
        """
        if not ids and not paths:
            raise ValueError("Must provide either file paths or product IDs and a directory")
        if ids and not directory:
            raise ValueError("Directory value missing")
        if directory is not None:
            directory = Path(directory)
        paths = [Path(p) for p in paths] if paths else []
        ids = ids or []

        # Get product IDs corresponding to the files on disk
        names = []
        if paths:
            names = [p.stem for p in paths]
            result = self._query_names(names)
            for product_dicts in result.values():
                ids += list(product_dicts)
        names_from_paths = set(names)
        ids = set(ids)

        # Collect the OData information for each product
        # Product name -> list of matching odata dicts
        product_infos = defaultdict(list)
        for id in ids:
            odata = self.get_product_odata(id)
            name = odata["title"]
            product_infos[name].append(odata)

            # Collect
            if name not in names_from_paths:
                paths.append(directory / self._get_filename(odata))

        # Now go over the list of products and check them
        corrupt = {}
        for path in paths:
            name = path.stem

            if len(product_infos[name]) > 1:
                self.logger.warning("%s matches multiple products on server", path)

            if not path.exists():
                # We will consider missing files as corrupt also
                self.logger.info("%s does not exist on disk", path)
                corrupt[str(path)] = product_infos[name]
                continue

            is_fine = False
            for product_info in product_infos[name]:
                if path.stat().st_size == product_info["size"] and self._md5_compare(
                    path, product_info["md5"]
                ):
                    is_fine = True
                    break
            if not is_fine:
                self.logger.info("%s is corrupt", path)
                corrupt[str(path)] = product_infos[name]
                if delete:
                    path.unlink()

        return corrupt

    def _md5_compare(self, file_path, checksum, block_size=2 ** 13):
        """Compare a given MD5 checksum with one calculated from a file."""
        file_path = Path(file_path)
        file_size = file_path.stat().st_size
        with self._tqdm(
            desc="MD5 checksumming", total=file_size, unit="B", unit_scale=True
        ) as progress:
            md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                while True:
                    block_data = f.read(block_size)
                    if not block_data:
                        break
                    md5.update(block_data)
                    progress.update(len(block_data))
            return md5.hexdigest().lower() == checksum.lower()

    def _download(self, url, path, file_size):
        headers = {}
        continuing = path.exists()
        if continuing:
            already_downloaded_bytes = path.stat().st_size
            headers = {"Range": "bytes={}-".format(already_downloaded_bytes)}
        else:
            already_downloaded_bytes = 0
        downloaded_bytes = 0
        with self.session.get(url, stream=True, headers=headers) as r, self._tqdm(
            desc="Downloading",
            total=file_size,
            unit="B",
            unit_scale=True,
            initial=already_downloaded_bytes,
        ) as progress:
            _check_scihub_response(r, test_json=False)
            chunk_size = 2 ** 20  # download in 1 MB chunks
            mode = "ab" if continuing else "wb"
            with open(path, mode) as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        progress.update(len(chunk))
                        downloaded_bytes += len(chunk)
            # Return the number of bytes downloaded
            return downloaded_bytes

    def _tqdm(self, **kwargs):
        """tqdm progressbar wrapper. May be overridden to customize progressbar behavior"""
        kwargs.update({"disable": not self.show_progressbars})
        return tqdm(**kwargs)

    def get_stream(self, id, **kwargs):
        """Exposes requests response ready to stream product to e.g. S3.

        Parameters
        ----------
        id : string
            UUID of the product, e.g. 'a8dd0cfd-613e-45ce-868c-d79177b916ed'
        **kwargs
            Any additional parameters for ``requests.get()``

        Raises
        ------
        LTATriggered
            If the product has been archived and its retrieval was successfully triggered.
        LTAError
            If the product has been archived and its retrieval failed.

        Returns
        -------
        requests.Response:
            Opened response object
        """
        is_online = not self.trigger_offline_retrieval(id)
        if not is_online:
            raise LTATriggered(id)
        r = self.session.get(self._get_download_url(id), stream=True, **kwargs)
        _check_scihub_response(r, test_json=False)
        return r

    def _get_odata_url(self, uuid, suffix=""):
        return self.api_url + f"odata/v1/Products('{uuid}')" + suffix

    def _get_download_url(self, uuid):
        return self._get_odata_url(uuid, "/$value")


def read_geojson(geojson_file):
    """Read a GeoJSON file into a GeoJSON object."""
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
        FeatureCollection), defaults to first feature
    decimals : int, optional
        Number of decimal figures after point to round coordinate to. Defaults to 4 (about 10
        meters).

    Returns
    -------
    str
        Well-Known Text string representation of the geometry
    """
    if "coordinates" in geojson_obj:
        geometry = geojson_obj
    elif "geometry" in geojson_obj:
        geometry = geojson_obj["geometry"]
    else:
        geometry = geojson_obj["features"][feature_number]["geometry"]

    def ensure_2d(geometry):
        if isinstance(geometry[0], (list, tuple)):
            return list(map(ensure_2d, geometry))
        else:
            return geometry[:2]

    def check_bounds(geometry):
        if isinstance(geometry[0], (list, tuple)):
            return list(map(check_bounds, geometry))
        else:
            if geometry[0] > 180 or geometry[0] < -180:
                raise ValueError("Longitude is out of bounds, check your JSON format or data")
            if geometry[1] > 90 or geometry[1] < -90:
                raise ValueError("Latitude is out of bounds, check your JSON format or data")

    # Discard z-coordinate, if it exists
    geometry["coordinates"] = ensure_2d(geometry["coordinates"])
    check_bounds(geometry["coordinates"])

    wkt = geomet.wkt.dumps(geometry, decimals=decimals)
    # Strip unnecessary spaces
    wkt = re.sub(r"(?<!\d) ", "", wkt)
    return wkt


def _format_query_value(attr, value):
    """Format the value of a Solr query parameter."""

    # Handle spaces by adding quotes around the string, if appropriate
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            raise ValueError(f"Trying to filter '{attr}' with an empty string")
        # Handle strings surrounded by brackets specially to allow the user to make use of Solr syntax directly.
        # The string must not be quoted for that to work.
        if (
            not any(
                value.startswith(s[0]) and value.endswith(s[1])
                for s in ["[]", "{}", "//", "()", '""']
            )
            and "*" not in value
            and "?" not in value
        ):
            value = re.sub(r"\s", " ", value, re.M)
            value = f'"{value}"'

    # Handle date keywords
    # Keywords from https://github.com/SentinelDataHub/DataHubSystem/search?q=text/date+iso8601
    is_date_attr = attr.lower() in [
        "beginposition",
        "endposition",
        "date",
        "creationdate",
        "ingestiondate",
    ]
    if is_date_attr:
        # Automatically format date-type attributes
        if isinstance(value, str) and " TO " in value:
            # This is a string already formatted as a date interval,
            # e.g. '[NOW-1DAY TO NOW]'
            pass
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            value = (format_query_date(value[0]), format_query_date(value[1]))
        else:
            raise ValueError(
                f"Date-type query parameter '{attr}' expects either a two-element tuple of "
                f"str or datetime objects or a '[<from> TO <to>]'-format string. Received {value}."
            )

    if isinstance(value, set):
        raise ValueError(f"Unexpected set-type value encountered with keyword '{attr}'")
    elif isinstance(value, (list, tuple)):
        # Handle value ranges
        if len(value) == 2:
            # Allow None or "*" to be used as an unlimited bound
            if any(x == "" for x in value):
                raise ValueError(f"Trying to filter '{attr}' with an empty string")
            value = ["*" if x in (None, "*") else f'"{x}"' for x in value]
            if value == ["*", "*"] or (is_date_attr and value == ["*", "NOW"]):
                # Drop this keyword if both sides are unbounded
                return
            value = "[{} TO {}]".format(*value)
        else:
            raise ValueError(
                f"Invalid number of elements in list. Expected 2, received {len(value)}"
            )
    return value


def format_query_date(in_date):
    r"""
    Format a date, datetime or a YYYYMMDD string input as YYYY-MM-DDThh:mm:ssZ
    or validate a date string as suitable for the full text search interface and return it.

    `None` will be converted to '\*', meaning an unlimited date bound in date ranges.

    Parameters
    ----------
    in_date : str or datetime or date or None
        Date to be formatted

    Returns
    -------
    str
        Formatted string

    Raises
    ------
    ValueError
        If the input date type is incorrect or passed date string is invalid
    """
    if in_date is None:
        return "*"
    if isinstance(in_date, (datetime, date)):
        return in_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif not isinstance(in_date, str):
        raise ValueError("Expected a string or a datetime object. Received {}.".format(in_date))

    in_date = in_date.strip()
    if in_date == "*":
        # '*' can be used for one-sided range queries e.g. ingestiondate:[* TO NOW-1YEAR]
        return in_date

    # Reference: https://cwiki.apache.org/confluence/display/solr/Working+with+Dates

    # ISO-8601 date or NOW
    valid_date_pattern = r"^(?:\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z|NOW)"
    # date arithmetic suffix is allowed
    units = r"(?:YEAR|MONTH|DAY|HOUR|MINUTE|SECOND)"
    valid_date_pattern += r"(?:[-+]\d+{}S?)*".format(units)
    # dates can be rounded to a unit of time
    # e.g. "NOW/DAY" for dates since 00:00 today
    valid_date_pattern += r"(?:/{}S?)*$".format(units)
    in_date = in_date.strip()
    if re.match(valid_date_pattern, in_date):
        return in_date

    try:
        return datetime.strptime(in_date, "%Y%m%d").strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ValueError("Unsupported date value {}".format(in_date))


def _check_scihub_response(response, test_json=True, query_string=None):
    """Check that the response from server has status code 2xx and that the response is valid JSON."""
    # Prevent requests from needing to guess the encoding
    # SciHub appears to be using UTF-8 in all of their responses
    response.encoding = "utf-8"
    try:
        response.raise_for_status()
        if test_json:
            response.json()
    except (requests.HTTPError, ValueError):
        msg = None
        try:
            msg = response.json()["error"]["message"]["value"]
        except Exception:
            try:
                msg = response.headers["cause-message"]
            except Exception:
                if not response.text.lstrip().startswith("{"):
                    try:
                        h = html2text.HTML2Text()
                        h.ignore_images = True
                        h.ignore_anchors = True
                        msg = h.handle(response.text).strip()
                    except Exception:
                        pass

        if msg is None:
            raise ServerError("Invalid API response", response)
        elif response.status_code == 401:
            msg = "Invalid user name or password"
            if "apihub.copernicus.eu/apihub" in response.url:
                msg += (
                    ". Note that account creation and password changes may take up to a week "
                    "to propagate to the 'https://apihub.copernicus.eu/apihub/' API URL you are using. "
                    "Consider switching to 'https://scihub.copernicus.eu/dhus/' instead in the mean time."
                )
            raise UnauthorizedError(msg, response)
        elif "Request Entity Too Large" in msg or "Request-URI Too Long" in msg:
            msg = "Server was unable to process the query due to its excessive length"
            if query_string is not None:
                length = SentinelAPI.check_query_length(query_string)
                msg += (
                    " (approximately {:.3}x times the maximum allowed). "
                    "Consider using SentinelAPI.check_query_length() for "
                    "client-side validation of the query string length.".format(length)
                )
            raise QueryLengthError(msg, response)
        elif "Invalid key" in msg:
            msg = msg.split(" : ", 1)[-1]
            raise InvalidKeyError(msg, response)
        elif 500 <= response.status_code < 600 or msg:
            # 5xx: Server Error
            raise ServerError(msg, response)
        else:
            raise SentinelAPIError(msg, response)


def _format_order_by(order_by):
    if not order_by or not order_by.strip():
        return None
    output = []
    for part in order_by.split(","):
        part = part.strip()
        dir = " asc"
        if part[0] == "+":
            part = part[1:]
        elif part[0] == "-":
            dir = " desc"
            part = part[1:]
        if not part or not part.isalnum():
            raise ValueError("Invalid order by value ({})".format(order_by))
        output.append(part + dir)
    return ",".join(output)


def _parse_gml_footprint(geometry_str):
    # workaround for https://github.com/sentinelsat/sentinelsat/issues/286
    if geometry_str is None:  # pragma: no cover
        return None
    geometry_xml = ET.fromstring(geometry_str)
    poly_coords_str = (
        geometry_xml.find("{http://www.opengis.net/gml}outerBoundaryIs")
        .find("{http://www.opengis.net/gml}LinearRing")
        .findtext("{http://www.opengis.net/gml}coordinates")
    )
    poly_coords = (coord.split(",")[::-1] for coord in poly_coords_str.split(" "))
    coord_string = ",".join(" ".join(coord) for coord in poly_coords)
    return "POLYGON(({}))".format(coord_string)


def _parse_iso_date(content):
    if "." in content:
        return datetime.strptime(content, "%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        return datetime.strptime(content, "%Y-%m-%dT%H:%M:%SZ")


def _parse_odata_timestamp(in_date):
    """Convert the timestamp received from OData JSON API to a datetime object."""
    timestamp = int(in_date.replace("/Date(", "").replace(")/", ""))
    seconds = timestamp // 1000
    ms = timestamp % 1000
    return datetime.utcfromtimestamp(seconds) + timedelta(milliseconds=ms)


def _parse_opensearch_response(products):
    """Convert a query response to a dictionary.

    The resulting dictionary structure is {<product id>: {<property>: <value>}}.
    The property values are converted to their respective Python types unless `parse_values`
    is set to `False`.
    """

    converters = {"date": _parse_iso_date, "int": int, "long": int, "float": float, "double": float}

    # Keep the string type by default
    def default_converter(x):
        return x

    output = OrderedDict()
    for prod in products:
        product_dict = {}
        prod_id = prod["id"]
        output[prod_id] = product_dict
        for key in prod:
            if key == "id":
                continue
            if isinstance(prod[key], str):
                product_dict[key] = prod[key]
            else:
                properties = prod[key]
                if isinstance(properties, dict):
                    properties = [properties]
                if key == "link":
                    for p in properties:
                        name = "link"
                        if "rel" in p:
                            name = "link_" + p["rel"]
                        product_dict[name] = p["href"]
                else:
                    f = converters.get(key, default_converter)
                    for p in properties:
                        try:
                            product_dict[p["name"]] = f(p["content"])
                        except KeyError:
                            # Sentinel-3 has one element 'arr'
                            # which violates the name:content convention
                            product_dict[p["name"]] = f(p["str"])
    return output


def _parse_odata_response(product):
    output = {
        "id": product["Id"],
        "title": product["Name"],
        "size": int(product["ContentLength"]),
        product["Checksum"]["Algorithm"].lower(): product["Checksum"]["Value"],
        "date": _parse_odata_timestamp(product["ContentDate"]["Start"]),
        "footprint": _parse_gml_footprint(product["ContentGeometry"]),
        "url": product["__metadata"]["media_src"],
        "Online": product.get("Online", True),
        "Creation Date": _parse_odata_timestamp(product["CreationDate"]),
        "Ingestion Date": _parse_odata_timestamp(product["IngestionDate"]),
    }
    # Parse the extended metadata, if provided
    converters = [int, float, _parse_iso_date]
    for attr in product["Attributes"].get("results", []):
        value = attr["Value"]
        for f in converters:
            try:
                value = f(attr["Value"])
                break
            except ValueError:
                pass
        output[attr["Name"]] = value
    return output


def placename_to_wkt(place_name):
    """Geocodes the place name to rectangular bounding extents using Nominatim API and
       returns the corresponding 'ENVELOPE' form Well-Known-Text.

    Parameters
    ----------
    place_name : str
        the query to geocode

    Raises
    ------
    ValueError
        If no matches to the place name were found.

    Returns
    -------
    wkt_envelope : str
        Bounding box of the location as an 'ENVELOPE(minX, maxX, maxY, minY)' WKT string.
    info : Dict[str, any]
        Matched location's metadata returned by Nominatim.
    """
    rqst = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place_name, "format": "geojson"},
        headers={"User-Agent": "sentinelsat/" + sentinelsat_version},
    )
    rqst.raise_for_status()
    features = rqst.json()["features"]
    if len(features) == 0:
        raise ValueError('Unable to find a matching location for "{}"'.format(place_name))
    # Get the First result's bounding box and description.
    feature = features[0]
    minX, minY, maxX, maxY = feature["bbox"]
    # ENVELOPE is a non-standard WKT format supported by Solr
    # https://lucene.apache.org/solr/guide/6_6/spatial-search.html#SpatialSearch-BBoxField
    wkt_envelope = "ENVELOPE({}, {}, {}, {})".format(minX, maxX, maxY, minY)
    info = feature["properties"]
    info["bbox"] = feature["bbox"]
    return wkt_envelope, info


def is_wkt(possible_wkt):
    pattern = r"^((MULTI)?(POINT|LINESTRING|POLYGON)|GEOMETRYCOLLECTION|ENVELOPE)\s*\(.+\)$"
    return re.match(pattern, possible_wkt.strip().upper()) is not None
