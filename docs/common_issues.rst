.. _common_issues:

Common Issues
=============

.. Using "rubric" directives as titles so they don't show on the TOC


.. rubric:: I keep getting *HTTP 401 Unauthorized* messages*

This means that the given username/password combination is incorrect or unknown at the given DHuS instance. Note that
if you created your account recently on the Copernicus Open Access Hub you can use the endpoint `dhus`__ right away,
but it takes about a week until the credentials are synced to the `apihub`__ endpoint.

__ https://scihub.copernicus.eu/dhus/

__ https://scihub.copernicus.eu/apihub/


.. rubric:: The query fails with *HTTP 500 connection timed out*

Commonly caused by server outages due to high demand. Try again later.

.. rubric:: Query fails with 'Longitude/Latitude is out of bounds, check your JSON format or data.'

Standard GeoJSON specification requires WGS84 coordinates, check if your data complies with it.


.. rubric:: My search returns 0 results

By default ``sentinelsat`` will query the last 24 hours. There might be no available images in that area for that time.
Try extending your search time period.


.. rubric:: Anything else?

Make sure to check the `issues on GitHub`__ too.

__ https://github.com/sentinelsat/sentinelsat/issues?q=is%3Aissue
