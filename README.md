# TwinSpect - Near-Duplicate Benchmark

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Documentation](https://img.shields.io/badge/docs-eval.iscc.codes-green.svg)](https://eval.iscc.codes)

*A comprehensive benchmarking framework for evaluating near-duplicate matching and similarity
search of text, audio, image, and video content based on compact binary codes.*

## Overview

**TwinSpect** was built to evaluate the
[International Standard Content Code (ISCC)](https://iscc.codes) and inform the ISO community
about its capabilities and performance characteristics across different media types.

The framework provides end-to-end evaluation of information retrieval metrics for compact binary
code algorithms against real-world and synthetically augmented media datasets.

**Live results:** https://eval.iscc.codes

## Features

- **Configurable benchmarks** - YAML-based configuration for algorithms, datasets, and metrics
- **Multi-modal support** - Text, audio, image, and video content types
- **Dataset management** - Automatic acquisition and transformation of public media collections
- **Fast similarity search** - HNSW-based indexing for approximate nearest-neighbor queries
- **Effectiveness metrics** - Precision, recall, F1 scores at configurable hamming thresholds
- **Result visualization** - Auto-generated documentation with charts and tables
- **Extensible architecture** - Plugin system for custom algorithms, datasets, and transformations
- **Performance optimized** - Parallel processing and intelligent caching of intermediate results

## Quick Start

**Requirements:** [Python 3.11+](https://python.org),
[uv](https://docs.astral.sh/uv/), and [ffmpeg](https://ffmpeg.org/) (for audio/video)

```bash
# Clone and install
git clone https://github.com/iscc/twinspect
cd twinspect
uv sync

# Run the full benchmark suite
uv run twinspect run
```

## CLI Usage

```bash
# List available components
uv run twinspect algorithms       # Show registered algorithms
uv run twinspect datasets         # Show available datasets
uv run twinspect benchmarks       # Show benchmark configurations
uv run twinspect transformations  # Show media transformations

# Run benchmarks
uv run twinspect run              # Execute all configured benchmarks

# Utilities
uv run twinspect version          # Show version
uv run twinspect info             # Show data folder information
uv run twinspect checksum <path>  # Compute folder checksum
```

## Bioimage conversion benchmark

The `bioimage_convert_1000` dataset builds 1000 same-source conversion clusters from public Broad
Bioimage Benchmark Collection sources. Each cluster contains the selected source bioimage plus
OME-TIFF, TIFF, PNG, JPEG 2000, DICOM and ICS variants converted with pinned
OME Bio-Formats bftools `8.5.0` using default conversion settings only.

TwinSpect downloads and verifies the bftools archive automatically on first use:

- URL: `https://downloads.openmicroscopy.org/bio-formats/8.5.0/artifacts/bftools.zip`
- SHA-256: `07a3bb1d3de84da3a709655a1008cb2d9b19becc5bad4ae4112633aec9380478`
- Default cache: `~/.cache/twinspect/bioformats`

Bio-Formats bftools is a Java distribution with Unix and Windows launchers (`bfconvert` and
`bfconvert.bat`). A working Java runtime is required. Custom converters are still supported via
`TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE` or `TWINSPECT_BIOIMAGE_CONVERT_BIN`; the binary override uses
the legacy `imgcnv -i INPUT -o OUTPUT -t FORMAT` argument shape, while arbitrary CLIs should use the
template override.

The benchmark measures same-source conversion robustness. It intentionally uses default
format conversions rather than synthetic edits, brightness shifts, blur, or custom compression
flags. On BBBC smoke runs with Bio-Formats defaults, OME-TIFF/TIFF/PNG/DICOM/ICS
generally preserve identical IMAGEWALK Data-Codes, while JPEG 2000 introduces converter drift
on some BMP sources. That negative/positive split is part of the benchmark pressure and keeps
the dataset semantics converter-induced rather than hand-edited.

## Documentation

The benchmark results and methodology are documented at **https://eval.iscc.codes**, including:

- Algorithm descriptions and configurations
- Dataset specifications and transformations
- Effectiveness metrics and interpretation
- Distribution analysis charts

## Development

```bash
# Install with dev dependencies
uv sync

# Run development tasks
uv run poe all              # Run all formatting and validation tasks
uv run poe format-code      # Format Python code with ruff
uv run poe format-yaml      # Format YAML files
uv run poe validate-schema  # Validate OpenAPI schema
uv run poe generate-code    # Generate Pydantic models from schema

# Preview documentation locally
uv run mkdocs serve
```

## Project Structure

```
twinspect/
├── algos/          # Algorithm implementations and processing
├── datasets/       # Dataset acquisition and management
├── metrics/        # Effectiveness and distribution metrics
├── render/         # Result rendering (Markdown, charts)
├── transformations/# Media transformation functions
├── config.yml      # Main benchmark configuration
└── schema.yml      # OpenAPI data model specification
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for
details.
