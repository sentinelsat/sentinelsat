import fnmatch
from pathlib import Path
from xml.etree import ElementTree as etree

import sentinelsat
from sentinelsat.exceptions import LTATriggered, SentinelAPIError
from sentinelsat.sentinel import _check_scihub_response


class SentinelProductsAPI(sentinelsat.SentinelAPI):
    """Class to connect to Copernicus Open Access Hub, search and download imagery.

    The products node interface allows to filter and download individual product
    files by means of a (optional) *nodefilter* callable function.
    For each file in the product (only excluding the manifest) the *nodefilter* function
    is called to decide if the corresponding file must be downloaded or not.

    The *nodefilter* function has the following signature::

      def nodefilter(node_info: dict) -> bool:
          ...

    The *node_info* parameter is a dictionary containing information like

    * the file *path* within the product (e.g. "./preview/map-overlay.kml")
    * the file size in bytes (int)
    * the file md5

    It the *nodefilter* function returns True the corresponding file is downloaded,
    otherwise the file is not downloaded.


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
    timeout : float or tuple, optional
        How long to wait for DataHub response (in seconds).
        Tuple (connect, read) allowed.

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


    .. versionadded:: 0.15
    """

    def _path_to_url(self, product_info, path, urltype=None):
        id = product_info["id"]
        title = product_info["title"]
        path = "/".join(["Nodes('{}')".format(item) for item in path.split("/")])
        if urltype == "value":
            urltype = "/$value"
        elif urltype == "json":
            urltype = "?$format=json"
        elif urltype == "full":
            urltype = "?$format=json&$expand=Attributes"
        elif urltype is None:
            urltype = ""
        # else: pass urltype as is
        return self._get_odata_url(id, f"/Nodes('{title}.SAFE')/{path}{urltype}")

    def _get_manifest(self, product_info, path=None):
        path = Path(path) if path else None
        url = self._path_to_url(product_info, "manifest.safe", "value")
        node_info = product_info.copy()
        node_info["url"] = url
        node_info["node_path"] = "./manifest.safe"
        del node_info["md5"]

        if path and path.exists():
            self.logger.info("manifest file already available (%r), skip download", path)
            data = path.read_bytes()
            node_info["size"] = len(data)
            return node_info, data

        url = self._path_to_url(product_info, "manifest.safe", "json")
        response = self.session.get(url, auth=self.session.auth)
        _check_scihub_response(response)
        info = response.json()["d"]

        node_info["size"] = int(info["ContentLength"])

        response = self.session.get(node_info["url"], auth=self.session.auth)
        _check_scihub_response(response, test_json=False)
        data = response.content
        if len(data) != node_info["size"]:
            raise SentinelAPIError("File corrupt: data length do not match")

        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        return node_info, data

    def _dataobj_to_node_info(self, dataobj_info, product_info):
        path = dataobj_info["href"]
        if path.startswith("./"):
            path = path[2:]

        node_info = product_info.copy()
        node_info["url"] = self._path_to_url(product_info, path, "value")
        node_info["size"] = dataobj_info["size"]
        node_info["md5"] = dataobj_info["md5"]
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

    def download(self, id, directory_path=".", checksum=True, nodefilter=None, **kwargs):
        """Download a product.

        Uses the filename on the server for the downloaded files, e.g.
        "S1A_EW_GRDH_1SDH_20141003T003840_20141003T003920_002658_002F54_4DD1.SAFE/manifest.safe".

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
        nodefilter : callable, optional
            The *nodefilter* callable used to select which file of each product have to
            be downloaded.
            If *nodefilter* is None then no file filtering is performed and the class
            behaves exactly as :class:`sentinelsat.sentinel.SentinelAPI`.


        Returns
        -------
        product_info : dict
            Dictionary containing the product's info from get_product_info() as well as
            the path on disk.

        Raises
        ------
        InvalidChecksumError
            If the MD5 checksum does not match the checksum on the server.
        """
        if nodefilter is None:
            return sentinelsat.SentinelAPI.download(self, id, directory_path, checksum, **kwargs)

        product_info = self.get_product_odata(id)
        product_path = Path(directory_path) / (product_info["title"] + ".SAFE")
        product_info["node_path"] = "./" + product_info["title"] + ".SAFE"
        manifest_path = product_path / "manifest.safe"
        if not manifest_path.exists() and self.trigger_offline_retrieval(id):
            raise LTATriggered(id)

        manifest_info, _ = self._get_manifest(product_info, manifest_path)
        product_info["nodes"] = {
            manifest_info["node_path"]: manifest_info,
        }

        node_infos = self._filter_nodes(manifest_path, product_info, nodefilter)
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

            self._download_outer(node_info, path, checksum)

        return product_info


def _xml_to_dataobj_info(element):
    assert etree.iselement(element)
    assert element.tag == "dataObject"
    data = dict(
        id=element.attrib["ID"],
        rep_id=element.attrib["repID"],
    )
    elem = element.find("byteStream")
    # data["mime_type"] = elem.attrib['mimeType']
    data["size"] = int(elem.attrib["size"])
    elem = element.find("byteStream/fileLocation")
    data["href"] = elem.attrib["href"]
    # data['locator_type'] = elem.attrib["locatorType"]
    # assert data['locator_type'] == "URL"

    elem = element.find("byteStream/checksum")
    assert elem.attrib["checksumName"].upper() == "MD5"
    data["md5"] = elem.text

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
