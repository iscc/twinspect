# TwinSpect - Near-Duplicate Benchmark

*A comprehensive benchmarking framework for evaluating near-duplicate matching and similarity search
of text, audio, image, and video content based on compact binary codes.*

## Introduction

The **TwinSpect** benchmark was built to evaluate the International Standard Content Code
(ISCC) and to inform the ISO community and ISCC users about the capabilities and performance
characteristics of the ISCC when applied to different media types.

After initial development the benchmark evolved into a comprehensive framework for end-to-end
evaluation of various information retrieval metrics for compact binary code algorithms against
real-world or syntheticaly augmented datasets of media files, including features like:

- YAML based benchmark configuration
- Acquisition and of public media file collections
- Clustering and synthetic transformations of media files
- Calculation of ISCC (and other) compact codes for media files
- HNSW based indexing of codes for fast approximate nearest-neighbor search
- Evaluating duplicate retrieval effectiveness and other metrics
- Rendering and presentation of benchmark results including documentation, graphs and tables.
- Extensibile Algorithms, Datasets, Transformations, and Metrics
- Caching of intermediary benchmark results
- Support for parallel data processing

The results of the default benchmak configuration are published at: https://eval.iscc.codes

## Running the Benchmark

To run the benchmark with its default configuration on your own system make sure you have
[Python 3.11](https://python.org) and [Poetry](https://python-poetry.org/) installed and use the
following commands:

```bash
git clone https://github.com/iscc/twinspect
cd twinspect
poetry install twinspect
poetry run python -m twinspect
```
