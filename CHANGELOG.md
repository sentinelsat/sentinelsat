# Change Log
All notable changes to `sentinelsat` will be listed here.

## [UNRELEASED]
### Added
- added a changelog

### Fixed
- docs represent new `query` and `download_all` behaviour

## [0.8] - 2017-01-27
### Changed
- `query` now returns a list of search results
- `download_all` requires the list of search results as an argument

### Removed
- `SentinelAPI` does not save query results as class attributes

## [0.7.4] - 2017-01-14
### Added
- Travis tests for Python 3.6

## [0.7.3] - 2016-12-09
### Changed
- changed `SentinelAPI` `max_rows` attribute to `page_size` to better reflect pagination
