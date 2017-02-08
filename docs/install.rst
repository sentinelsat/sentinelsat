.. _installation:

Installation
============

Sentinelsat depends on `homura <https://github.com/shichao-an/homura>`_, which
depends on `PycURL <http://pycurl.sourceforge.net/>`_. When the dependencies are
fulfilled install with ``pip install sentinelsat``.

Unix
----

Ubuntu
~~~~~~

.. code-block:: console

    sudo apt-get install build-essential libcurl4-openssl-dev python-dev python-pip

Fedora
~~~~~~
.. code-block:: console

    sudo yum groupinstall "Development Tools"
    sudo yum install libcurl libcurl-devel python-devel python-pip


Windows
-------

The easiest way to install pycurl is with
`pycurl wheels <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl>`_ provided by
Christoph Gohlke

.. code-block:: console

    pip install pycurl.whl

or with `Conda <http://conda.pydata.org/docs/>`_.

.. code-block:: console

    conda install pycurl


OSX
---

TODO: How to install on OSX.

Tests
-----

.. code-block:: bash

  git clone https://github.com/sentinelsat/sentinelsat.git
  cd sentinelsat
  pip install -e .[test]
  export SENTINEL_USER=<username>
  export SENTINEL_PASSWORD=<password>
  py.test -v -m "not homura"


Running all tests, including tests for downloading functionality, requires Copernicus Open Access Hub
credentials to be provided via environment variables.

.. code-block:: bash

  export SENTINEL_USER=<username>
  export SENTINEL_PASSWORD=<password>
  py.test -v


Supported Python versions
-------------------------

Sentinelsat has been tested with Python versions 2.7 and 3.4+. Earlier Python 3 versions are
expected to work as well as long as the dependencies are fulfilled.

Optional dependencies
---------------------

The convenience functions ``to_dataframe()`` and ``to_geodataframe()`` require ``pandas`` and/or
``geopandas`` to be present.


Troubleshooting
---------------

Download from the Copernicus Open Access Hub will fail if the server certificate cannot be verified
because no default CA bundle is defined, as on Windows, or when the CA bundle is
outdated. In most cases the easiest solution is to install or update ``certifi``:

``pip install -U certifi``
You can also override the the path setting to the PEM file of the CA bundle
using the ``pass_through_opts`` keyword argument when calling ``api.download()``
or ``api.download_all()``:

.. code-block:: python

  from pycurl import CAINFO
  api.download_all(products, pass_through_opts={CAINFO: 'path/to/my/cacert.pem'})
