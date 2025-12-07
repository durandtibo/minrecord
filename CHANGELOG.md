# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial CHANGELOG.md file

## [0.1.0] - 2024-XX-XX

### Added
- `RecordManager` class to manage multiple records
- `get_best_values` and `get_last_values` functional utilities
- `get_max_size` and `set_max_size` configuration functions
- Support for Python 3.10, 3.11, 3.12, 3.13, and 3.14

### Changed
- Minimum Python version is now 3.10 (was 3.9 in 0.0.x)
- Updated `coola` dependency to `>=0.9.2a0,<1.0`

## [0.0.2] - 2024-XX-XX

### Added
- Initial comparable record implementations (`MaxScalarRecord`, `MinScalarRecord`)
- Generic `Record` class for tracking recent values
- `ComparableRecord` base class with comparator pattern
- Base comparators (`MaxScalarComparator`, `MinScalarComparator`)

### Changed
- Updated dependencies

## [0.0.1] - 2024-XX-XX

### Added
- Initial release
- Base record interface (`BaseRecord`)
- Core functionality for tracking values in ML workflows

[Unreleased]: https://github.com/durandtibo/minrecord/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/durandtibo/minrecord/compare/v0.0.2...v0.1.0
[0.0.2]: https://github.com/durandtibo/minrecord/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/durandtibo/minrecord/releases/tag/v0.0.1
