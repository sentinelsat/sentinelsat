.. _common_issues:

Common Issues
=============

.. Using "rubric" directives as titles so they don't show on the TOC


.. rubric:: I keep getting *HTTP 401 Unauthorized* messages*

This means that the given username/password combination is incorrect. Note that
if you created your account recently it could take a while (a few days?) until
you can use that account on *apihub* and therefore ``sentinelsat`` too. You can go
`here`__ to test access on the *apihub* endpoint.

__ https://scihub.copernicus.eu/apihub/search?


.. rubric:: The query fails with *HTTP 500 connection timed out*

SciHub servers are known to have outages due to high demand, try again later.

.. rubric:: Query fails with 'Longitude/Latitude is out of bounds, check your JSON format or data.'

Standard GeoJSON specification contains only WGS84 format, check if your data complies with it.


.. rubric:: My search returns 0 results

Maybe there are no images for the specified time period, by default
``sentinelsat`` will query the last 24 hours only.

.. rubric:: The query fails with 'Query request is too large, reduce query datapoints'

There are too complex polygons in the query. Please reduce your .geojson file to less than 200 points.

.. rubric:: Anything else?

Make sure to check the `issues on GitHub`__ too.

__ https://github.com/sentinelsat/sentinelsat/issues?q=is%3Aissue
