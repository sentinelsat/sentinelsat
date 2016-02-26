.. _installation:

Installation
============

Sentinelsat depends on `homura <https://github.com/shichao-an/homura>`_, which depends on `PycURL <http://pycurl.sourceforge.net/>`_.

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

The easiest way to install pycurl is to use one of the `pycurl wheels <http://www.lfd.uci.edu/~gohlke/pythonlibs/#pycurl>`_ provided by Christoph Gohlke.

.. code-block:: console

    pip install pycurl.whl

Or you can use `Conda <http://conda.pydata.org/docs/>`_ and do

.. code-block:: console

    conda install pycurl

Then install ``sentinelsat``:

.. code-block:: console

    pip install sentinelsat

OSX
---

TODO: How to install on OSX.

Troubleshooting
---------------

TODO: Common installation errors and how to solve them.
