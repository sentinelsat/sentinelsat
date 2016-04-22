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

The easiest way to install pycurl is to use one of the
`pycurl wheels <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl>`_ provided by
Christoph Gohlke.

.. code-block:: console

    pip install pycurl.whl

Or you can use `Conda <http://conda.pydata.org/docs/>`_ and do

.. code-block:: console

    conda install pycurl


OSX
---

TODO: How to install on OSX.

Tests
-----

.. code-block:: bash

  git clone https://github.com/ibamacsr/sentinelsat.git
  cd sentinelsat
  pip install -e .[test]
  export SENTINEL_USER=<your scihub username>
  export SENTINEL_PASSWORD=<your scihub password>
  py.test -v


Troubleshooting
---------------

The download from Scihub will fail if the server certificate cannot be verified
because no default CA bundle is defined, as on Windows, or when the CA bundle is
outdated. In most cases the easiest solution is to install or update ``certifi``:

``pip install -U certifi``
You can also override the the path setting to the PEM file of the CA bundle
using the ``pass_through_opts`` keyword argument when calling ``api.download()``
or ``api.download_all()``:

.. code-block:: python

  from pycurl import CAINFO
  api.download_all(pass_through_opts={CAINFO: 'path/to/my/cacert.pem'})
