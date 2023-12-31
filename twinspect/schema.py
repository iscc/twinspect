# generated by datamodel-codegen:
#   filename:  schema.yml

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import AnyUrl, BaseModel, Field


class Mode(Enum):
    text = "text"
    image = "image"
    audio = "audio"
    video = "video"


class Benchmark(BaseModel):
    algorithm_label: str = Field(
        ..., description="The Algorithm to evaluate referenced by its label"
    )
    dataset_label: str = Field(
        ...,
        description="The Dataset against which to evaluate the Algorithm referenced by its label",
    )
    metric_labels: List = Field(
        ..., description="A list of metrics to calculate for the benchmark referenced by label"
    )
    active: bool = Field(
        ..., description="Whether the benchmark should be executed during full benchmark run"
    )


class Metric(BaseModel):
    name: Optional[str] = Field(None, description="A short readable name of the metric")
    label: Optional[str] = Field(
        None, description="Short unique label used to reference the metric"
    )
    function: Optional[str] = Field(
        None, description="Full path to python function that that calculates the metric"
    )


class Effectivness(BaseModel):
    threshold: Optional[int] = Field(
        None, description="The maximum hamming distance threshold of the measurement"
    )
    recall: Optional[float] = Field(
        None, description="How many retrieved items are relevant (0-None, 1-All)"
    )
    precision: Optional[float] = Field(
        None, description="How many retrieved items are relevant (0-None, 1-All)"
    )
    f1_score: Optional[float] = Field(
        None,
        alias="f1-score",
        description="Harmonic mean of precision and recall (0-Worst, 1-Best)",
    )


class Algorithm(BaseModel):
    name: str = Field(..., description="The name of the Algorithms")
    label: str = Field(..., description="Short labes used in tables and for file names")
    mode: Mode
    function: str = Field(
        ...,
        description="Full path to python function that implements the algorithm. The function must accept a file path as the first parameter and must return a hex encoded compact hash code.",
    )
    dependencies: Optional[List[str]] = Field(
        None, description="A list of python package dependencies required by the implementation"
    )


class Task(BaseModel):
    id: int = Field(..., description="The id of the media file")
    code: Optional[str] = Field(None, description="The genrated hex encoded compact binary code")
    file: str = Field(..., description="The root relative file path of the media file")
    size: Optional[int] = Field(
        None, description="The file size of the media file in number of bytes"
    )
    time: Optional[int] = Field(
        None, description="The processing duration for code generation in milliseconds"
    )


class Dataset(BaseModel):
    name: str = Field(..., description="The name of the dataset")
    label: Optional[str] = Field(None, description="Short label used in tables and as folder name")
    info: Optional[str] = Field(None, description="Human readable information about the dataset")
    url: AnyUrl = Field(..., description="Download url for dataset")
    mode: Mode
    installer: Optional[str] = Field(
        None, description="Full path to python function that installs the dataset"
    )
    samples: Optional[int] = Field(
        None, description="Number of samples to install from the dataset"
    )
    clusters: Optional[int] = Field(
        None, description="Number of similarity clusters to build for dataset"
    )
    seed: Optional[int] = Field(
        None, description="Seed for reproducible random selection of samples"
    )
    checksum: Optional[str] = Field(None, description="Checksum of datafolder")


class Transformation(BaseModel):
    name: str = Field(..., description="The name of the transformation")
    label: str = Field(..., description="Short unique label to identify the transformation")
    info: Optional[str] = Field(
        None, description="Human readable information about the transformation"
    )
    mode: Mode
    function: str = Field(
        ..., description="Full path to python function that applies the transformation"
    )
    params: Optional[List] = Field(
        None, description="A list of transformation parameters to be used with the function"
    )


class Configuration(BaseModel):
    twinspect: str = Field(..., description="Configuration file format version")
    algorithms: Optional[List[Algorithm]] = Field(
        None, description="List of algorithms to be benchmarked"
    )
    datasets: List[Dataset] = Field(..., description="List of Datasets")
    transformations: List[Transformation] = Field(..., description="List of Transformations")
    metrics: Optional[List[Metric]] = None
    benchmarks: Optional[List[Benchmark]] = Field(None, description="A list of Benchmarks to run")


class Distribution(BaseModel):
    min: Optional[int] = Field(None, description="The minimum value.")
    max: Optional[int] = Field(None, description="The maximum value.")
    mean: Optional[float] = Field(None, description="The mean value.")
    median: Optional[float] = Field(None, description="The median value.")


class DatasetInfo(BaseModel):
    dataset_label: str = Field(
        ..., description="Dataset label (directory name) used as identifier for the dataset"
    )
    dataset_mode: str = Field(
        ..., description="Inferred perceptual mode of dataset (text, image, audio, video)"
    )
    total_size: int = Field(..., description="Total size of data-folder in number of bytes.")
    total_files: int = Field(..., description="The total count of all media files in the dataset.")
    total_clusters: int = Field(..., description="The total count of clusters in the dataset.")
    cluster_sizes: Distribution = Field(
        ..., description="The distribution of sizes of the clusters."
    )
    total_distractor_files: int = Field(
        ..., description="The count of top-level files that are not part of any cluster."
    )
    ratio_cluster_to_distractor: float = Field(
        ..., description="The ratio of cluster files to distractor files."
    )
    transformations: Optional[List[str]] = Field(
        None, description="List of unique transformation labels inferred from the filenames."
    )
    checksum: str = Field(..., description="64-Bit hex encoded checksum of data-folder.")
