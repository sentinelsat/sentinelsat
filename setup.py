from codecs import open as codecs_open
from setuptools import setup, find_packages


# Get the long description from the relevant file
with codecs_open('README.rst', encoding='utf-8') as f:
    long_description = f.read()


setup(name='sentinelsat',
      version='0.4',
      description="Utility to search and download Sentinel-1 Imagery",
      long_description=long_description,
      classifiers=[
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Topic :: Scientific/Engineering :: GIS',
          'Topic :: Utilities',
      ],
      keywords='',
      author="Wille Marcel",
      author_email='wille@wille.blog.br',
      url='https://github.com/ibamacsr/sentinelsat',
      license='GPLv3+',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'requests',
          'click',
          'homura>=0.1.2',
          'certifi',
          'geojson'
      ],
      extras_require={
          'test': ['pytest'],
      },
      entry_points="""
      [console_scripts]
      sentinel=sentinelsat.scripts.cli:cli
      """
      )
