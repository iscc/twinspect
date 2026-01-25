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
