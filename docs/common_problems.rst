.. _common_problems:

Common problems
===============

.. Using "rubric" directives as titles so they don't show on the TOC


.. rubric:: I keep getting *HTTP 401 Unauthorized* messages

This means that the given username/password combination is incorrect. Note that
if you created your account recently it could take a while (a few days?) until
you can use that account on *apihub* and therefore *sentinelsat* too. You can go
`here`__ to test access on the *apihub* endpoint.

__ https://scihub.copernicus.eu/apihub/search?


.. rubric:: The query fails with *HTTP 500 connect time out*

Scihub servers are known to have outages due to high demand, try again later.


.. rubric:: How I can see the images?

Take a look at the `Sentinel Toolbox`__.

__ https://sentinel.esa.int/web/sentinel/toolboxes/sentinel-2


.. rubric:: My search returns 0 results

Maybe there are no images for the specified time period, by default
*sentinelsat* will query the last 24 hours only.


.. rubric:: Anything else?

Make sure to check the `issues on GitHub`__ too.

__ https://github.com/sentinelsat/sentinelsat/issues
