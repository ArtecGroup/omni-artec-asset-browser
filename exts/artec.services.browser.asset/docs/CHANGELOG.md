# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [1.2.7] - 2021-04-11
### Changed
- Remove sync callss

## [1.2.6] - 2021-03-30
### Changed
- Republish for repo updates

## [1.2.5] - 2022-02-19
### Changed
- Avoid timeout when downloading large asset

## [1.2.4] - 2022-02-18
### Added
- Download progress callback

## [1.2.3] - 2022-02-10
### Changed
- Do not run callback if no assets found in folder when running collection

## [1.2.2] - 2022-01-25
### Added
- Adds download endpoint

## [1.2.1] - 2021-01-25
### Added
- New API "config" to config provider
### Changed
- Get provider setting from "provider" API

## [1.1.4] - 2021-01-17
### Added
- Search returns not only list of asset models but also if more

## [1.1.3] - 2021-01-17
### Changed
- Move asset providers to extensions

## [1.1.2] - 2021-01-14
### Added
- Added filter to only return downloadable assets from SketchFab.
### Changed
- Enforced maximum of 24 search results for the public SketchFab API, as required by the API constraints.

## [1.1.1] - 2021-01-14
### Added
- API to get vendor list
### Changed
- S3 search with no category and keywords
- Sketchfab search with no category and fix sort issue

## [1.1.0] - 2021-01-13
### Added
- Added support for SketchFab asset search.

## [1.0.1] - 2021-01-13
### Changed
- For TurboSquid assets, always search by keywords for category

## [1.0.0] - 2021-12-12
### Added
- Remove no longer supported list and features endpoints.
- Implement basic search functionality for Dummy and JSON based stores.
- Change assetgroup facility to support searching multiple store simultaniously.

## [0.1.0] - 2021-09-19
### Added
- Added initial version of the Extension.
