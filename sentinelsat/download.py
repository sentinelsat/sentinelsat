import concurrent.futures
import enum
import fnmatch
import itertools
import shutil
import threading
import traceback
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict
from xml.etree import ElementTree as etree

from sentinelsat.exceptions import (
    InvalidChecksumError,
    LTAError,
    LTATriggered,
    SentinelAPIError,
    ServerError,
    UnauthorizedError,
)


class DownloadStatus(enum.Enum):
    """Status info for ``SentinelAPI.download_all()``."""

    UNAVAILABLE = enum.auto()
    OFFLINE = enum.auto()
    TRIGGERED = enum.auto()
    ONLINE = enum.auto()
    DOWNLOAD_STARTED = enum.auto()
    DOWNLOADED = enum.auto()

    def __bool__(self):
        return self == DownloadStatus.DOWNLOADED


class Downloader:
    def __init__(
        self,
        api,
        directory_path=".",
        *,
        node_filter=None,
        verify_checksum=True,
        fail_fast=False,
        max_attempts=10,
        n_concurrent_dl=2,
        n_concurrent_trigger=1,
        lta_retry_delay=60
    ):
        """

        Parameters
        ----------
        directory_path : string, optional
            Where the file will be downloaded
        checksum : bool, optional
            If True, verify the downloaded file's integrity by checking its MD5 checksum.
            Throws InvalidChecksumError if the checksum does not match.
            Defaults to True.
        """
        from sentinelsat import SentinelAPI

        self.api: SentinelAPI = api
        self.logger = self.api.logger
        self._tqdm = self.api._tqdm

        self.directory = directory_path
        self.node_filter = node_filter
        self.verify_checksum = verify_checksum
        self.fail_fast = fail_fast
        self.max_attempts = max_attempts
        self._n_concurrent_dl = n_concurrent_dl
        self.n_concurrent_trigger = n_concurrent_trigger
        self.lta_retry_delay = lta_retry_delay

        # The bounded semaphore is needed on top of the thread pool because
        # downloading and triggering both count against the maximum number of
        # concurrent GET queries on the server side.
        self._dl_semaphore = threading.BoundedSemaphore(self._n_concurrent_dl)

    @property
    def n_concurrent_dl(self):
        return self._n_concurrent_dl

    @n_concurrent_dl.setter
    def n_concurrent_dl(self, value):
        self._n_concurrent_dl = value
        self._dl_semaphore = threading.BoundedSemaphore(self._n_concurrent_dl)

    def download(self, id):
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
            Dictionary containing the product's info from get_product_odata() as well as
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
        if not self.node_filter:
            product_info = self.api.get_product_odata(id)
            filename = self.api._get_filename(product_info)
            path = Path(self.directory) / filename
            product_info["path"] = str(path)
            product_info["downloaded_bytes"] = 0

            self.logger.info("Downloading %s to %s", id, path)

            if path.exists():
                # We assume that the product has been downloaded and is complete
                return product_info

            # An incomplete download triggers the retrieval from the LTA if the product is not online
            if not self.api.is_online(id):
                self.trigger_offline_retrieval(id)
                raise LTATriggered(id)

            self._download_outer(product_info, path)
            return product_info
        else:
            product_info = self.api.get_product_odata(id)
            product_path = Path(self.directory) / (product_info["title"] + ".SAFE")
            product_info["node_path"] = "./" + product_info["title"] + ".SAFE"
            manifest_path = product_path / "manifest.safe"
            if not manifest_path.exists() and self.trigger_offline_retrieval(id):
                raise LTATriggered(id)

            manifest_info, _ = self.api._get_manifest(product_info, manifest_path)
            product_info["nodes"] = {
                manifest_info["node_path"]: manifest_info,
            }

            node_infos = self._filter_nodes(manifest_path, product_info, self.node_filter)
            product_info["nodes"].update(node_infos)

            for node_info in node_infos.values():
                node_path = node_info["node_path"]
                path = (product_path / node_path).resolve()
                node_info["path"] = path
                node_info["downloaded_bytes"] = 0

                self.logger.info("Downloading %s node to %s", id, path)
                self.logger.debug("Node URL for %s: %s", id, node_info["url"])

                if path.exists():
                    # We assume that the product node has been downloaded and is complete
                    continue
                self._download_outer(node_info, path)
            return product_info

    def _download_outer(self, product_info: Dict[str, Any], path: Path):
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
                if self.verify_checksum and not self.api._checksum_compare(temp_path, product_info):
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
        if self.verify_checksum is True:
            if not self.api._checksum_compare(temp_path, product_info):
                temp_path.unlink()
                raise InvalidChecksumError("File corrupt: checksums do not match")
        # Download successful, rename the temporary file to its proper name
        shutil.move(temp_path, path)
        return product_info

    def download_all(self, products):
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
        fail_fast : bool, optional
            if True, all other downloads are cancelled when one of the downloads fails.
            Defaults to False.
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

        ResultTuple = namedtuple("ResultTuple", ["statuses", "exceptions", "product_infos"])
        product_ids = list(set(products))
        assert self.n_concurrent_dl > 0
        if len(product_ids) == 0:
            return ResultTuple({}, {}, {})
        self.logger.info(
            "Will download %d products using %d workers", len(product_ids), self.n_concurrent_dl
        )

        statuses = {pid: DownloadStatus.UNAVAILABLE for pid in product_ids}
        exceptions = {}
        product_infos = {}
        online_prods = set()
        offline_prods = set()

        # Get online status and product info.
        for pid in self._tqdm(
            iterable=product_ids, desc="Fetching archival status", unit="product"
        ):
            assert isinstance(pid, str)
            try:
                info = self.api.get_product_odata(pid)
            except UnauthorizedError:
                raise
            except SentinelAPIError as e:
                exceptions[pid] = e
                if self.fail_fast:
                    raise
                self.logger.error(
                    "Getting product info for %s failed, can't download: %s",
                    pid,
                    _format_exception(e),
                )
                continue
            product_infos[pid] = info
            if product_infos[pid]["Online"]:
                statuses[pid] = DownloadStatus.ONLINE
                online_prods.add(pid)
            else:
                statuses[pid] = DownloadStatus.OFFLINE
                offline_prods.add(pid)

        # Skip already downloaded files.
        # Although the download method also checks, we do not need to retrieve such
        # products from the LTA and use up our quota.
        for pid in list(offline_prods):
            product_info = product_infos[pid]
            filename = self.api._get_filename(product_info)
            path = Path(self.directory) / filename
            if path.exists():
                self.logger.info("Skipping already downloaded %s.", filename)
                product_info["path"] = str(path)
                statuses[pid] = DownloadStatus.DOWNLOADED
                offline_prods.remove(pid)
            else:
                self.logger.info(
                    "%s (%s) is in LTA and will be triggered.", product_info["title"], pid
                )

        stop_event = threading.Event()
        dl_tasks = {}
        trigger_tasks = {}

        trigger_progress = None
        if offline_prods:
            trigger_progress = self._tqdm(
                total=len(offline_prods),
                desc="Retrieving from archive",
                unit="product",
                leave=True,
            )
        dl_progress = self._tqdm(
            total=len(online_prods) + len(offline_prods),
            desc="Downloading products",
            unit="product",
        )
        dl_progress.clear()

        # Two separate threadpools for downloading and triggering of retrieval.
        # Otherwise triggering might take up all threads and nothing is downloaded.
        with ThreadPoolExecutor(
            max_workers=self.n_concurrent_dl, thread_name_prefix="dl"
        ) as dl_executor, ThreadPoolExecutor(
            max_workers=self.n_concurrent_trigger, thread_name_prefix="trigger"
        ) as trigger_executor:
            # First all online products are downloaded. Subsequently, offline products that might
            # have become available in the meantime are requested.
            for pid in itertools.chain(online_prods, offline_prods):
                future = dl_executor.submit(
                    self._download_online_retry,
                    product_infos[pid],
                    statuses,
                    exceptions,
                    stop_event,
                )
                dl_tasks[future] = pid

            for pid in offline_prods:
                future = trigger_executor.submit(
                    self._trigger_and_wait,
                    pid,
                    stop_event,
                    statuses,
                )
                trigger_tasks[future] = pid

            all_tasks = list(trigger_tasks) + list(dl_tasks)
            try:
                for task in concurrent.futures.as_completed(all_tasks):
                    pid = trigger_tasks.get(task) or dl_tasks[task]
                    exception = exceptions.get(pid)
                    if task.cancelled():
                        exception = concurrent.futures.CancelledError()
                    if task.exception():
                        exception = task.exception()

                    if task in dl_tasks:
                        dl_progress.update()
                        if not exception:
                            product_infos[pid] = task.result()
                            statuses[pid] = DownloadStatus.DOWNLOADED
                    elif task in trigger_tasks:
                        trigger_progress.update()
                        if all(t.done() for t in trigger_tasks):
                            trigger_progress.close()

                    if exception:
                        exceptions[pid] = exception
                        if self.fail_fast:
                            raise exception from None
                        else:
                            self.logger.error("%s failed: %s", pid, _format_exception(exception))
            except:
                stop_event.set()
                for t in all_tasks:
                    t.cancel()
                raise
            finally:
                if trigger_progress:
                    trigger_progress.close()
                dl_progress.close()

        if not any(statuses):
            if not exceptions:
                raise SentinelAPIError("Downloading all products failed for an unknown reason")
            exception = list(exceptions)[0]
            raise exception

        return ResultTuple(statuses, exceptions, product_infos)

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
        # Request just a single byte to avoid accidental downloading of the whole product.
        # Requesting zero bytes results in NullPointerException in the server.
        with self._dl_semaphore:
            r = self.api.session.get(
                self.api._get_download_url(uuid), headers={"Range": "bytes=0-1"}
            )
        cause = r.headers.get("cause-message")
        # check https://scihub.copernicus.eu/userguide/LongTermArchive#HTTP_Status_codes
        if r.status_code in (200, 206):
            self.logger.debug("Product is online")
            return False
        elif r.status_code == 202:
            self.logger.debug("Accepted for retrieval")
            return True
        elif r.status_code == 403 and cause and "concurrent flows" in cause:
            # cause: 'An exception occured while creating a stream: Maximum number of 4 concurrent flows achieved by the user "username""'
            self.logger.debug("Product is online but concurrent downloads limit was exceeded")
            return False
        elif r.status_code == 403:
            # cause: 'User 'username' offline products retrieval quota exceeded (20 fetches max) trying to fetch product PRODUCT_FILENAME (BYTES_COUNT bytes compressed)'
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
        self.api._check_scihub_response(r, test_json=False)

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
        if not self.api.is_online(id):
            self.trigger_offline_retrieval(id)
            raise LTATriggered(id)
        with self._dl_semaphore:
            r = self.api.session.get(self.api._get_download_url(id), stream=True, **kwargs)
        self.api._check_scihub_response(r, test_json=False)
        return r

    def download_quicklook(self, id):
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
        product_info = self.api.get_product_odata(id)
        url = product_info["quicklook_url"]

        path = Path(self.directory) / "{}.jpeg".format(product_info["title"])
        product_info["path"] = str(path)
        product_info["downloaded_bytes"] = 0
        product_info["error"] = ""

        self.logger.info("Downloading quicklook %s to %s", product_info["title"], path)

        with self._dl_semaphore:
            r = self.api.session.get(url)
        self.api._check_scihub_response(r, test_json=False)

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

    def download_all_quicklooks(self, products):
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

        with ThreadPoolExecutor(max_workers=self.n_concurrent_dl) as dl_exec:
            dl_tasks = {}
            for pid in products:
                future = dl_exec.submit(self.download_quicklook, pid)
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

    def _trigger_and_wait(self, uuid, stop_event, statuses):
        """Continuously triggers retrieval of offline products

        This function is supposed to be called in a separate thread. By setting stop_event it can be stopped.
        """
        while not self.api.is_online(uuid) and not stop_event.is_set():
            if statuses[uuid] == DownloadStatus.OFFLINE:
                # Trigger
                try:
                    triggered = self.trigger_offline_retrieval(uuid)
                    if triggered:
                        statuses[uuid] = DownloadStatus.TRIGGERED
                        self.logger.info("%s accepted for retrieval", uuid)
                    else:
                        # Product is already online
                        break
                except (LTAError, ServerError) as e:
                    if isinstance(e, ServerError) and "NullPointerException" not in e.msg:
                        # LTA retrieval frequently fails with HTTP 500 NullPointerException intermittently
                        raise
                    self.logger.info(
                        "Request for %s was not accepted: %s. Retrying in %d seconds",
                        uuid,
                        e.msg,
                        self.lta_retry_delay,
                    )
            else:
                # Just wait for the product to come online
                pass
            stop_event.wait(timeout=self.lta_retry_delay)
        if not stop_event.is_set():
            self.logger.info("%s retrieval from LTA completed", uuid)
            statuses[uuid] = DownloadStatus.ONLINE

    def _download_online_retry(self, product_info, statuses, exceptions, stop_event):
        """Thin wrapper around download with retrying and checking whether a product is online

        Parameters
        ----------

        product_info : dict
            Contains the product's info as returned by get_product_odata()
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
        if self.max_attempts <= 0:
            return

        uuid = product_info["id"]
        title = product_info["title"]

        # Wait for the triggering and retrieval to complete first
        while (
            statuses[uuid] != DownloadStatus.ONLINE
            and uuid not in exceptions
            and not stop_event.is_set()
        ):
            stop_event.wait(timeout=1)
        if uuid in exceptions:
            return

        last_exception = None
        for cnt in range(self.max_attempts):
            if stop_event.is_set():
                return
            try:
                statuses[uuid] = DownloadStatus.DOWNLOAD_STARTED
                return self.download(uuid)
            except Exception as e:
                if isinstance(e, InvalidChecksumError):
                    self.logger.warning(
                        "Invalid checksum. The downloaded file for '%s' is corrupted.",
                        title,
                    )
                else:
                    self.logger.exception("There was an error downloading %s", title)
                self.logger.info("%d retries left", self.max_attempts - cnt - 1)
                last_exception = e
        self.logger.info("No retries left for %s. Terminating.", title)
        raise last_exception

    def _download(self, url, path, file_size):
        headers = {}
        continuing = path.exists()
        if continuing:
            already_downloaded_bytes = path.stat().st_size
            headers = {"Range": "bytes={}-".format(already_downloaded_bytes)}
        else:
            already_downloaded_bytes = 0
        downloaded_bytes = 0
        with self._dl_semaphore:
            with self.api.session.get(url, stream=True, headers=headers) as r, self._tqdm(
                desc="Downloading",
                total=file_size,
                unit="B",
                unit_scale=True,
                initial=already_downloaded_bytes,
            ) as progress:
                self.api._check_scihub_response(r, test_json=False)
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

    def _dataobj_to_node_info(self, dataobj_info, product_info):
        path = dataobj_info["href"]
        if path.startswith("./"):
            path = path[2:]

        node_info = product_info.copy()
        node_info["url"] = self.api._path_to_url(product_info, path, "value")
        node_info["size"] = dataobj_info["size"]
        if "md5" in dataobj_info:
            node_info["md5"] = dataobj_info["md5"]
        if "sha3-256" in dataobj_info:
            node_info["sha3-256"] = dataobj_info["sha3-256"]
        node_info["node_path"] = dataobj_info["href"]
        # node_info["parent"] = product_info

        return node_info

    def _filter_nodes(self, manifest, product_info, nodefilter=None):
        nodes = {}
        xmldoc = etree.parse(manifest)
        data_obj_section_elem = xmldoc.find("dataObjectSection")
        for elem in data_obj_section_elem.iterfind("dataObject"):
            dataobj_info = _xml_to_dataobj_info(elem)
            node_info = self._dataobj_to_node_info(dataobj_info, product_info)
            if nodefilter is not None and not nodefilter(node_info):
                continue
            node_path = node_info["node_path"]
            nodes[node_path] = node_info
        return nodes


def _xml_to_dataobj_info(element):
    assert etree.iselement(element)
    assert element.tag == "dataObject"
    data = dict(
        id=element.attrib["ID"],
    )
    elem = element.find("byteStream")
    # data["mime_type"] = elem.attrib['mimeType']
    data["size"] = int(elem.attrib["size"])
    elem = element.find("byteStream/fileLocation")
    data["href"] = elem.attrib["href"]
    # data['locator_type'] = elem.attrib["locatorType"]
    # assert data['locator_type'] == "URL"

    elem = element.find("byteStream/checksum")
    assert elem.attrib["checksumName"].upper() in ["MD5", "SHA3-256"]
    data[elem.attrib["checksumName"].lower()] = elem.text

    return data


def make_size_filter(max_size):
    """Generate a nodefilter function to download only files below the specified maximum size.

    .. versionadded:: 0.15
    """

    def node_filter(node_info):
        return node_info["size"] <= max_size

    return node_filter


def make_path_filter(pattern, exclude=False):
    """Generate a nodefilter function to download only files matching the specified pattern.

    Parameters
    ----------
    pattern : str
        glob patter for files selection
    exclude : bool, optional
        if set to True then files matching the specified pattern are excluded. Default False.

    .. versionadded:: 0.15
    """

    def node_filter(node_info):
        match = fnmatch.fnmatch(node_info["node_path"].lower(), pattern)
        return not match if exclude else match

    return node_filter


def all_nodes_filter(node_info):
    """Node filter function to download all files.

    This function can be used to download Sentinel product as a directory
    instead of downloading a single zip archive.

    .. versionadded:: 0.15
    """
    return True


def _format_exception(ex):
    return "".join(traceback.TracebackException.from_exception(ex).format())
