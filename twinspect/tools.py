# -*- coding: utf-8 -*-
from contextlib import contextmanager
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from runpy import run_module
from typing import Callable
import mmap
import os
import sys
import importlib
from pathlib import Path
from loguru import logger as log
import blake3
import twinspect as ts


__all__ = [
    "result_path",
    "get_data_folder",
    "get_function",
    "load_function",
    "install_algorithm",
    "datasets",
    "count_files",
    "hash_file",
    "iter_original_files",
]


@cache
def result_path(algo_label, data_folder, extension, tag=None, checksum=None):
    # type: (str, str|Path, str, str|None, str | None) -> Path
    """Construct a result file path for a given benchmark based on data_folder checksum"""
    algo_label = algo_label.split(":")[-1]
    data_folder = Path(data_folder)
    dataset_label = data_folder.name
    checksum = ts.check_dir_fast(data_folder, expected=checksum)
    stem = f"{algo_label}-{dataset_label}-{checksum}"
    suffix = f"-{tag}.{extension}" if tag else f".{extension}"
    return ts.opts.root_folder / f"{stem}{suffix}"


@contextmanager
def silence():
    """Context manager for silenceing console output."""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull

        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def get_data_folder(dataset):
    # type: (ts.Dataset) -> Path
    """Return absolute data_folder path for a given Dataset"""
    return ts.opts.root_folder / dataset.label


def get_function(algoritm):
    # type: (ts.Algorithm) -> Callable
    """Return the callable function of an algorithm implementation"""
    return load_function(algoritm.function)


def load_function(path: str):
    module_path, function_name = path.split(":")
    module = importlib.import_module(module_path)
    function = getattr(module, function_name)
    return function


def aquire_dataset(dataset: ts.Dataset) -> Path:
    install = load_function(dataset.installer)
    return install(dataset)


def install_algorithm(algorithm: ts.Algorithm):
    for dep in algorithm.dependencies:
        package_name, required_version = dep.split("==")
        try:
            installed_version = version(package_name)
            if installed_version == required_version:
                log.trace(f"{package_name} v{required_version} already installed")
                continue
            else:
                raise PackageNotFoundError
        except PackageNotFoundError:
            log.debug(f"Installing {dep}")
            log.warning(f"Please re-run TwinSpect after installation.")
            with silence():
                sys.argv = ["pip", "install", dep]
                run_module("pip", run_name="__main__")


def datasets(mode: ts.Mode):
    return [ds for ds in ts.cnf.datasets if ds.mode == mode]


def count_files(path: Path) -> int:
    """Count number of files in path recursively"""
    file_count = 0
    for root, dirs, files in os.walk(path):
        file_count += len(files)
    return file_count


def iter_original_files(data_folder: Path):
    """Iterate over clusters in a data_folder and yield original files"""
    for subdir in data_folder.iterdir():
        if subdir.is_dir():
            files = list(subdir.glob("*"))
            if files:
                sorted_files = sorted(files)
                yield sorted_files[0]


def hash_file(file_path: Path) -> bytes:
    """Create hash for file at file_path"""
    file_path = Path(file_path)
    with file_path.open("r+b") as infile:
        mm = mmap.mmap(infile.fileno(), 0, access=mmap.ACCESS_READ)
        return blake3.blake3(mm, max_threads=blake3.blake3.AUTO).digest(8)
