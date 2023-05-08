# -*- coding: utf-8 -*-
"""Extended Schema Objects with convenience methods"""
import functools
from pathlib import Path
from typing import Optional, List, Set, Callable
from pydantic import BaseModel, Field
from twinspect.schema import Benchmark as BenchmarkBase
from twinspect.schema import Dataset as DatasetBase
from twinspect.schema import Algorithm as AlgorithmBase
from twinspect.schema import Transformation as TransformationBase
from twinspect.schema import Metric, Mode, Task


class Benchmark(BenchmarkBase):
    @property
    def dataset(self):
        import twinspect as ts

        for ds in ts.cnf.datasets:
            if ds.label == self.dataset_label:
                return ds

    @property
    def algorithm(self):
        import twinspect as ts

        for algo in ts.cnf.algorithms:
            if algo.label == self.algorithm_label:
                return algo

    def simprint(self) -> Path:
        """Compute simprint file for benchmark"""
        import twinspect as ts

        return ts.simprint(self)

    def filepath(self, extension, tag=None):
        # type: (str, str|None) -> Path
        """Generate dataset anchored result file path with `extension`"""
        import twinspect as ts

        return ts.result_path(self.algorithm.label, self.dataset.data_folder, extension, tag)


class Algorithm(AlgorithmBase):
    def __hash__(self):
        return hash(self.label)

    def install(self):
        import twinspect as ts

        ts.install_algorithm(self)


class Transformation(TransformationBase):
    class Config(TransformationBase.Config):
        keep_untouched = (functools.cached_property,)

    @staticmethod
    @functools.cache
    def from_label(label):
        # type: (str) -> Transformation
        """Get Transformation object by its label"""
        import twinspect as ts

        for ts_obj in ts.cnf.transformations:
            if ts_obj.label == label:
                return ts_obj

    @staticmethod
    def for_mode(mode):
        # type: (Mode) -> List[Transformation]
        """Collect all transformations for a perceptual mode"""
        import twinspect as ts

        return [ts_obj for ts_obj in ts.cnf.transformations if ts_obj.mode == mode]

    @functools.cached_property
    def func_obj(self):
        # type: () -> Callable
        """Return the function object that does the transformation"""
        import twinspect as ts

        return ts.load_function(self.function)

    def apply(self, file_path):
        # type: (Path) -> Path
        """Apply transformation to file"""
        if self.params:
            return self.func_obj(file_path, *self.params)
        else:
            return self.func_obj(file_path)


class Dataset(DatasetBase):
    def __hash__(self):
        return hash(self.label)

    @property
    def data_folder(self):
        # type () -> Path
        """Construct path to data folder"""
        import twinspect as ts

        return ts.opts.root_folder / self.label

    def install(self):
        # type: () -> Path
        """Get final data_folder for dataset."""
        import twinspect as ts

        func = ts.load_function(self.installer)
        return func(dataset=self)


class Configuration(BaseModel):
    """
    Benchmarking Configuration

    Note:
        We are redifine the entire auto generated Configuration class to reference extended models.
    """

    twinspect: str = Field(..., description="Configuration file format version")
    algorithms: Optional[List[Algorithm]] = Field(
        None, description="List of algorithms to be benchmarked"
    )
    datasets: List[Dataset] = Field(..., description="List of Datasets")
    transformations: List[Transformation] = Field(..., description="List of Transformations")
    metrics: Optional[List[Metric]] = None
    benchmarks: Optional[List[Benchmark]] = Field(None, description="A list of Benchmarks to run")

    @property
    def active_benchmarks(self):
        # type: () -> List[Benchmark]
        return [bm for bm in self.benchmarks if bm.active]

    @property
    def active_algorithms(self):
        # type: () -> Set[Algorithm]
        return set(bm.algorithm for bm in self.active_benchmarks)

    @property
    def active_datasets(self):
        # type: () -> Set[Dataset]
        return set(bm.dataset for bm in self.active_benchmarks)
