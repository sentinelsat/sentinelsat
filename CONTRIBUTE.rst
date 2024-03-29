Welcome to the ``sentinelsat`` open source project. We invite anyone to participate by contributing code, reporting bugs, fixing bugs, writing documentation and tutorials and discussing the future of this project.


Issue Conventions
=================

Please search existing issues, open and closed, before creating a new one.

Providing a Short, Self Contained, Correct (Compilable), Example (`SSCCE <http://sscce.org/>`_) demonstrating the issue is encouraged.

``sentinelsat`` is not ``v1.0``. There may be backwards incompatible changes which you can find in the changelog (`CHANGELOG.rst <https://github.com/sentinelsat/sentinelsat/blob/main/CHANGELOG.rst>`_). We invite you to propose changes and features you would like to see in ``v1.0``.


Design Principles
=================

- ``sentinelsat`` is meant to be a Pythonic client to the `Copernicus Open Access Hub <https://scihub.copernicus.eu/dhus>`_ and other manifestations of  the `Data Hub System (DHuS) <http://sentineldatahub.github.io/DataHubSystem>`_.
- ``sentinelsat`` should interface the functions of DHuS where possible, rather than replicating them in Python.
- all code must be Python 3 compliant but we strive for backwards compatibility with Python 2 where possible

Contributing
============

If you want to contribute code or documentation the proposed way is:

1. `Fork <https://help.github.com/articles/fork-a-repo/>`_ the repository.
2. Create a `branch <https://help.github.com/articles/creating-and-deleting-branches-within-your-repository/>`_ and make your changes in it.
3. Create a `pull request <https://help.github.com/articles/creating-a-pull-request-from-a-fork/>`_.

If you plan on introducing major changes it is a good idea to create an issue first and discuss these changes with other contributors.

Code Conventions
================

``sentinelsat`` supports Python 2 and Python 3 in the same code base.

We strongly prefer code adhering to `PEP8 <https://www.python.org/dev/peps/pep-0008/>`_. We use a line-length of 100 and `black <https://github.com/python/black>`_ to format our code.

Tests are mandatory for new features. We use `pytest <https://pytest.org>`_ and `Travis-CI <https://travis-ci.org/>`_.
All unit tests must use prerecorded responses to Copernicus Open Access Hub. We use `VCR.py <https://github.com/kevin1024/vcrpy>`_ to record the responses.
We aspire to 100% coverage but regard meaningful tests to be more important than reaching this goal. Test coverage is tracked with `Codecov <https://codecov.io/gh/sentinelsat/sentinelsat>`_.

We keep a changelog (`CHANGELOG.rst <https://github.com/sentinelsat/sentinelsat/blob/main/CHANGELOG.rst>`_) following the `keepachangelog <http://keepachangelog.com>`_ template.

Good documentation is important to us. We use `Sphinx <http://www.sphinx-doc.org>`_ and host the documentation at `sentinelsat.readthedocs.io <https://sentinelsat.readthedocs.io/en/main/>`_.
All public functions should have docstrings. We use the `numpy docstring standard <https://github.com/numpy/numpy/blob/main/doc/HOWTO_DOCUMENT.rst.txt#docstring-standard>`_.

Development Environment
=======================

We prefer developing with the most recent version of Python. ``sentinelsat`` currently supports Python >= 3.5.

Initial Setup
-------------

First, clone ``sentinelsat``'s ``git`` repo:

.. code-block:: console

  git clone https://github.com/sentinelsat/sentinelsat


Development should occur within a `virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_ (venv, conda, etc.) to better isolate development work from your regular Python environments.

Installing sentinelsat
----------------------

``sentinelsat`` and its dependencies can be installed with ``pip``. Specifying the ``[dev]`` extra in the command below tells
``pip`` to also install ``sentinelsat``'s dev dependencies.

.. code-block:: console

  cd sentinelsat/
  pip install -e .[dev]


Running the tests
-----------------

``sentinelsat``'s tests are located in ``/tests``.

To run the tests

.. code-block:: console

  pytest -v

You can run individual tests with the syntax:

.. code-block:: console

  pytest -v /tests/test_file.py::test_you_want_to_run

This can be useful for recording or modifying individual vcr cassettes.

By default, prerecorded responses to Copernicus Open Access Hub queries are used to not be affected by its downtime.
Furthermore, any network accesses are blocked as well (by raising a ``pytest_socket.SocketBlockedError: A test tried to use socket.socket`` exception) to guarantee that all tests are indeed correctly covered by recorded queries.

To allow the tests to run actual queries against the Copernicus Open Access Hub set the environment variables and add ``--disable-vcr`` to ``pytest`` arguments.

.. code-block:: console

  export DHUS_USER=<username>
  export DHUS_PASSWORD=<password>
  pytest -v --disable-vcr


To update the recordings use ``--vcr-record`` with ``once``, ``new_episodes`` or ``all``. See `vcrpy docs <https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes>`_ for details.

When you create a pull requests the tests will automatically run on `Travis <https://travis-ci.org/sentinelsat/sentinelsat>`_ and a coverage report will be created from `Codecov <https://codecov.io/gh/sentinelsat/sentinelsat>`_.


Formatting the code
-------------------

The easiest way to follow ``sentinsat``'s code formatting conventions is to use the <https://github.com/python/black>`_ code formatter before creating a pull request.

.. code-block:: console

  pip install black
  black .

If you have docker installed you can alternatively run

.. code-block:: console

  docker run -it --rm --user "$(id -u):$(id -g)" -w "$PWD" -v "$PWD:$PWD" cytopia/black .

Versioning and Release
======================

``sentinelsat`` uses `semantic versioning <http://semver.org/>`_ from the ``v1.0`` release forward. Prior to that the versioning is ``0.Major.MinorAndPatch``.

Version numbers need to be adapted in sentinelsat/__init__.py as well as the Github compare link in the Readme.

Documentation is automatically built after each merge in the ``main`` branch using a webhook. The documentation landing page is set to ``stable``, which defaults to the latest release.

A new Zenodo DOI is created automatically with every Github release using the Zenodo webhook.

A new version is published to PyPI automatically via CI on every GitHub release.

Release checklist
-----------------

* Update the package version at https://github.com/sentinelsat/sentinelsat/blob/main/sentinelsat/__init__.py#L1
* Update the link to latest changes on the main branch under https://github.com/sentinelsat/sentinelsat#changelog
* Make sure docs are up to date and are rendered correctly at https://sentinelsat.readthedocs.io/en/main/
* Make sure all notable changes are covered in CHANGELOG.rst and update the version number there
* Update AUTHORS.rst
* Copy the relevant part of changelog into the release description and create a new release
* Start a new "Unreleased" version section in changelog

License
=======

The GNU General Public License version 3 or later (GPLv3+, see `LICENSE <https://github.com/sentinelsat/sentinelsat/blob/main/LICENSE>`_) applies to all contributions.
