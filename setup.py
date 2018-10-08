import re
from io import open

from setuptools import find_packages, setup

# Get the long description from the relevant file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

with open('sentinelsat/__init__.py', encoding='utf-8') as f:
    version = re.search(r"__version__\s*=\s*'(\S+)'", f.read()).group(1)

setup(name='sentinelsat',
      version=version,
      description="Utility to search and download Copernicus Sentinel satellite images",
      long_description=long_description,
      classifiers=[
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Topic :: Scientific/Engineering :: GIS',
          'Topic :: Utilities',
      ],
      keywords='copernicus, sentinel, esa, satellite, download, GIS',
      author="Kersten Clauss",
      author_email='kersten.clauss@gmail.com',
      url='https://github.com/sentinelsat/sentinelsat',
      license='GPLv3+',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=open('requirements.txt').read().splitlines(),
      extras_require={
          'dev': [
              'pandas',
              'geopandas',
              'shapely',
              'pytest >= 3.6.3',
              'pytest-socket',
              'requests-mock',
              'vcrpy',
              'rstcheck',
              'sphinx >= 1.3',
              'sphinx_rtd_theme'
          ],
          # Pandas and its dependencies are not available for Python <= 3.4
          'dev34': [
              'pytest >= 3.6.3',
              'pytest-socket',
              'requests-mock',
              'vcrpy',
              'rstcheck',
              'sphinx >= 1.3',
              'sphinx_rtd_theme'
          ]
      },
      entry_points="""
      [console_scripts]
      sentinelsat=sentinelsat.scripts.cli:cli
      """
      )
