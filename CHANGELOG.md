# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - Unreleased

Major modernization release after 3 years of dormancy.

### Added

- **Ensemble algorithms**: Support for combining multiple simprints into ensemble codes with
  checksum-based version matching to prevent mixing stale component outputs
- **TurboLameDuck**: Exact hamming search implementation using usearch library for improved
  performance
- **Semantic Image Code (iscc-sci)**: New algorithm for semantic image similarity matching
- **Auto-generated documentation**: Algorithms page now auto-generated from config.yml
- **Intra/inter-cluster separation**: Distribution plots now show separate intra-cluster and
  inter-cluster distance distributions for better analysis

### Changed

- **Results documentation**: Restructured from single page to multi-page layout organized by media
  type (text, image, audio, video) with a central overview page
- **Build system**: Migrated from Poetry to uv for faster dependency resolution and installation
- **Markdown formatting**: Switched to mdformat-mkdocs for consistent documentation formatting
- **Metrics calculation**: Now uses macro-averaged effectiveness metrics for unbiased evaluation
  across different cluster sizes
- **Documentation**: Improved chart documentation for non-technical users
- **Embedded images**: Optimized image sizes in documentation

### Removed

- Unused datasets removed from documentation and configuration
- Extra benchmark artifacts cleaned up to match live configuration

## [0.1.0] - 2023-08-24

Initial public release of the TwinSpect benchmarking framework.

### Added

- Core benchmarking pipeline with 6 stages: configuration, algorithm acquisition, dataset
  acquisition, media processing, benchmarking, and rendering
- Plugin architecture for algorithms, datasets, transformations, and metrics
- Support for text, audio, image, and video content types
- FAISS-based approximate nearest neighbor search (LameDuck/HammingHero)
- Audio transformations: trim, fade, transcode, master
- Dataset support: FMA (Free Music Archive), StreetLib
- Parallel file processing with simprint caching
- Effectiveness metrics: precision, recall, F1 at configurable hamming thresholds
- MkDocs-based documentation site
- OpenAPI schema for data models with auto-generated Pydantic code

[0.2.0]: https://github.com/iscc/twinspect/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/iscc/twinspect/releases/tag/v0.1.0
