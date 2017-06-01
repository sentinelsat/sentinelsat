.. _installation:

Installation
============

Install ``sentinelsat`` through pip:

.. code-block:: console

    pip install sentinelsat

Tests
-----

To run the tests on ``sentinelsat``:

.. code-block:: console

    git clone https://github.com/sentinelsat/sentinelsat.git
    cd sentinelsat
    pip install -e .[test]
    py.test -v

By default, prerecorded responses to Copernicus Open Access Hub queries are used to not be affected by its downtime.
To allow the tests to run actual queries against Copernicus Open Access Hub set the environment variables

.. code-block:: bash
    export SENTINEL_USER=<your scihub username>
    export SENTINEL_PASSWORD=<your scihub password>

and add ``--vcr disable`` to ``py.test`` arguments.
To update the recordings use either ``--vcr record_new`` or ``--vcr reset``.

Supported Python versions
-------------------------

Sentinelsat has been tested with Python versions 2.7 and 3.4+. Earlier Python 3 versions are
expected to work as well as long as the dependencies are fulfilled.

Optional dependencies
---------------------

The convenience functions ``to_dataframe()`` and ``to_geodataframe()`` require ``pandas`` and/or
``geopandas`` to be present.