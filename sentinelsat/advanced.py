# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import os
import shutil
from xml.etree import ElementTree as etree

import sentinelsat
from sentinelsat.sentinel import InvalidChecksumError, _check_scihub_response
from sentinelsat.exceptions import SentinelAPIError


def _xml_to_dataobj_info(element):
    assert etree.iselement(element)
    assert element.tag == "dataObject"
    data = dict(
        id=element.attrib["ID"],
        rep_id=element.attrib['repID'],
    )
    elem = element.find("byteStream")
    # data["mime_type"] = elem.attrib['mimeType']
    data["size"] = int(elem.attrib['size'])
    elem = element.find("byteStream/fileLocation")
    data['href'] = elem.attrib["href"]
    # data['locator_type'] = elem.attrib["locatorType"]
    # assert data['locator_type'] == "URL"

    elem = element.find("byteStream/checksum")
    assert elem.attrib["checksumName"].upper() == "MD5"
    data['md5'] = elem.text

    return data


class AdvancedSentinelAPI(sentinelsat.SentinelAPI):
    """Class to connect to Copernicus Open Access Hub, search and download imagery.

    The advanced interface allows to filter and download individual product files
    by means of a (optional) *nodefilter* callable function.
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
        defaults to 'https://scihub.copernicus.eu/apihub'
    show_progressbars : bool
        Whether progressbars should be shown or not, e.g. during download. Defaults to True.
    timeout : float or tuple, optional
        How long to wait for DataHub response (in seconds).
        Tuple (connect, read) allowed.
    nodefilter : callable, optional
        The *nodefilter* callable that is used to select which file of each product
        have to be downloaded.

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
    nodefilter : callable ot None
        If *nodefilter* is None no file filtering is performed and the class behaves
        exactly as :class:`SentinelAPI`.
        Otherwise the *nodefilter* callable is used to select which file of each product
        have to be downloaded.


    .. versionadded:: 0.15
    """
    def __init__(self, *args, **kwargs):
        self.nodefilter = kwargs.pop("nodefilter", None)
        sentinelsat.SentinelAPI.__init__(self, *args, **kwargs)

    def _path_to_url(self, product_info, path, urltype=None):
        data = dict(id=product_info["id"], title=product_info["title"])
        data["api_url"] = self.api_url
        data["path"] = "/".join(["Nodes('{}')".format(item) for item in path.split("/")])
        if urltype == 'value':
            data["urltype"] = "/$value"
        elif urltype == 'json':
            data["urltype"] = "?$format=json"
        elif urltype == 'full':
            data["urltype"] = "?$format=json&$expand=Attributes"
        elif urltype is None:
            data["urltype"] = ''
        else:
            data["urltype"] = urltype
        return "{api_url}odata/v1/Products('{id}')/Nodes('{title}.SAFE')/{path}{urltype}".format(**data)

    def _get_manifest(self, product_info, path=None):
        url = self._path_to_url(product_info, "manifest.safe", 'value')
        node_info = product_info.copy()
        node_info["url"] = url
        node_info["node_path"] = os.path.join(".", "manifest.safe")
        del node_info["md5"]

        if path and os.path.exists(path):
            self.logger.info("manifest file already available (%r), skip download", path)
            with open(path, "rb") as fd:
                data = fd.read()
            node_info["size"] = len(data)
        else:
            url = self._path_to_url(product_info, "manifest.safe", 'json')
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
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as fd:
                    fd.write(data)

        return node_info, data

    def _dataobj_to_node_info(self, dataobj_info, product_info):
        path = dataobj_info["href"]
        if path.startswith('./'):
            path = path[2:]

        node_info = product_info.copy()
        node_info["url"] = self._path_to_url(product_info, path, 'value')
        node_info["size"] = dataobj_info["size"]
        node_info["md5"] = dataobj_info["md5"]
        node_info["node_path"] = dataobj_info["href"]
        # node_info["parent"] = product_info

        return node_info

    def _filter_nodes(self, manifest, product_info, nodefilter=None):
        if nodefilter is None:
            nodefilter = self.nodefilter

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

    def download(self, id, directory_path=".", checksum=True):
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
        if self.nodefilter is None:
            return sentinelsat.SentinelAPI.download(self, id, directory_path, checksum)

        product_info = self.get_product_odata(id)
        product_path = os.path.join(directory_path, product_info["title"] + ".SAFE")
        product_info["node_path"] = os.path.join(".", product_info["title"] + ".SAFE")
        manifest_path = os.path.join(product_path, "manifest.safe")
        if not os.path.exists(manifest_path) and not product_info["Online"]:
            self.logger.warning(
                "Product %s is not online. Triggering retrieval from long term archive.",
                product_info["id"],
            )
            self._trigger_offline_retrieval(product_info["url"])
            return product_info

        manifest_info, _ = self._get_manifest(product_info, manifest_path)
        product_info["nodes"] = {
            manifest_info["node_path"]: manifest_info,
        }

        node_infos = self._filter_nodes(manifest_path, product_info, self.nodefilter)
        product_info["nodes"].update(node_infos)

        for node_info in node_infos.values():
            node_path = node_info["node_path"]
            path = os.path.join(product_path, os.path.normpath(node_path))
            node_info["path"] = path
            node_info["downloaded_bytes"] = 0

            self.logger.info("Downloading %s node to %s", id, path)
            self.logger.debug("Node URL for %s: %s", id, node_info["url"])

            if os.path.exists(path):
                # We assume that the product node has been downloaded and is complete
                continue

            # Use a temporary file for downloading
            temp_path = path + ".incomplete"

            skip_download = False
            if os.path.exists(temp_path):
                if os.path.getsize(temp_path) > node_info["size"]:
                    self.logger.warning(
                        "Existing incomplete file %s is larger than the expected final size"
                        " (%s vs %s bytes). Deleting it.",
                        str(temp_path),
                        os.path.getsize(temp_path),
                        node_info["size"],
                    )
                    os.remove(temp_path)
                elif os.path.getsize(temp_path) == node_info["size"]:
                    if checksum is True and not self._md5_compare(temp_path, node_info["md5"]):
                        # Log a warning since this should never happen
                        self.logger.warning(
                            "Existing incomplete file %s appears to be fully downloaded but "
                            "its checksum is incorrect. Deleting it.",
                            str(temp_path),
                        )
                        os.remove(temp_path)
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
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                node_info["downloaded_bytes"] = self._download(
                    node_info["url"], temp_path, self.session, node_info["size"]
                )

            # Check integrity with MD5 checksum
            if checksum is True:
                if not self._md5_compare(temp_path, node_info["md5"]):
                    os.remove(temp_path)
                    raise InvalidChecksumError("File corrupt: checksums do not match")

            # Download successful, rename the temporary file to its proper name
            shutil.move(temp_path, path)

        return product_info


def make_size_filter(max_size):
    """Generate a nodefilter function to download only files below the specified maximum size.

    .. versionadded:: 0.15
    """
    def node_filter(node_info, size=max_size):
        if node_info["size"] <= size:
            return True
        else:
            return False
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
    if exclude:
        def node_filter(node_info, exclude_pattern=pattern):
            import fnmatch
            if not fnmatch.fnmatch(node_info["node_path"].lower(), exclude_pattern):
                return True
            else:
                return False
    else:
        def node_filter(node_info, include_pattern=pattern):
            import fnmatch
            if fnmatch.fnmatch(node_info["node_path"].lower(), include_pattern):
                return True
            else:
                return False

    return node_filter


def all_nodes_filter(node_info):
    """Node filter function to download all files.

    This function can be used to download Sentinel product as a directory
    instead of downloading a single zip archive.

    .. versionadded:: 0.15
    """
    return True
