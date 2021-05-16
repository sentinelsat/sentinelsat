class SentinelAPIError(Exception):
    """Invalid response from DataHub. Base class for more specific exceptions.

    Attributes
    ----------
    msg: str
        The error message.
    response: requests.Response
        The response from the server as a `requests.Response` object.
    """

    def __init__(self, msg="", response=None):
        self.msg = msg
        self.response = response

    def __str__(self):
        if self.response is None:
            return self.msg
        if self.response.reason:
            reason = " " + self.response.reason
        else:
            reason = ""
        return "HTTP status {}{}: {}".format(
            self.response.status_code,
            reason,
            ("\n" if "\n" in self.msg else "") + self.msg,
        )


class LTAError(SentinelAPIError):
    """Error raised when retrieving a product from the Long Term Archive"""

    pass


class LTATriggered(SentinelAPIError):
    """Download failed due to product being in the Long Term Archive and retrieval from LTA was triggered"""

    def __init__(self, uuid):
        self.uuid = uuid
        super().__init__(
            f"Product {uuid} is not online. Triggered retrieval from the Long Term Archive."
        )


class ServerError(SentinelAPIError):
    """Error raised when the server responded in an unexpected manner, typically due to undergoing maintenance"""

    pass


class UnauthorizedError(SentinelAPIError):
    """Error raised when attempting to retrieve a product with incorrect credentials"""

    def __str__(self):
        return self.msg


class QuerySyntaxError(SentinelAPIError, SyntaxError):
    """Error raised when the query string could not be parsed on the server side"""

    def __init__(self, msg, response):
        SentinelAPIError.__init__(self, msg, response)
        SyntaxError.__init__(self, msg)

    def __str__(self):
        return self.msg


class QueryLengthError(SentinelAPIError):
    """Error raised when the query string length was excessively long"""

    def __str__(self):
        return self.msg


class InvalidKeyError(SentinelAPIError, KeyError):
    """Error raised when product with given key was not found on the server"""

    def __init__(self, msg, response):
        SentinelAPIError.__init__(self, msg, response)
        KeyError.__init__(self, msg)

    def __str__(self):
        return self.msg


class InvalidChecksumError(Exception):
    """MD5 checksum of a local file does not match the one from the server."""

    pass
