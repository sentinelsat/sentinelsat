"""Client for GNSS data."""

import logging

from .sentinel import SentinelAPI, _check_scihub_response


class GnssAPI(SentinelAPI):
    """Class to connect to Copernicus Open Access Hub, search and download GNSS data.

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
        defaults to 'https://scihub.copernicus.eu/gnss'
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
    """

    logger = logging.getLogger("sentinelsat.GnssAPI")

    def __init__(
        self,
        user: str = "gnssguest",
        password: str = "gnssguest",
        api_url: str = "https://scihub.copernicus.eu/gnss/",
        show_progressbars: bool = True,
        timeout: bool = None,
    ):
        super().__init__(user, password, api_url, show_progressbars, timeout)

    def download(self, id, directory_path=".", checksum=True, **kwargs):
        file_ext = kwargs.pop("file_ext", ".EOF")
        return super().download(id, directory_path, checksum, file_ext=file_ext, **kwargs)

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
        file_ext = kwargs.pop("file_ext", ".EOF")
        return super().download_all(
            products,
            directory_path,
            max_attempts,
            checksum,
            n_concurrent_dl,
            lta_retry_delay,
            file_ext=file_ext,
            **kwargs
        )

    def _get_filename(self, product_info):
        # Default guess, mostly for archived products
        filename = product_info["title"] + ".EOF"
        if not product_info["Online"]:
            return filename
        return super()._get_filename(product_info)
