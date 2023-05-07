# -*- coding: utf-8 -*-
from contextlib import contextmanager
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
import ruamel.yaml
import twinspect as ts


__all__ = [
    "get_data_folder",
    "get_function",
    "load_function",
    "install_algorithm",
    "datasets",
    "count_files",
    "hash_file",
    "iter_original_files",
]

ROOT = Path(__file__).parent.parent.absolute()


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


def format_yml():
    """Format all .yml files"""
    yaml = ruamel.yaml.YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 95
    yaml.allow_unicode = True
    yaml.default_flow_style = False
    yaml.default_style = None
    yaml.sort_keys = False

    for f in ROOT.glob("**/*.yml"):
        with open(f, "rt", encoding="utf-8") as infile:
            data = yaml.load(infile)
        with open(f, "wt", encoding="utf-8", newline="\n") as outf:
            yaml.dump(data, outf)


def fix_line_endings():
    """Normalize all line endings to unix LF"""
    WINDOWS_LINE_ENDING = b"\r\n"
    UNIX_LINE_ENDING = b"\n"
    extensions = {".py", ".toml", ".lock", ".md", ".yml", ".yaml"}
    for fp in ROOT.glob("**/*"):
        if fp.suffix in extensions:
            with open(fp, "rb") as infile:
                content = infile.read()
            new_content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
            if new_content != content:
                with open(fp, "wb") as outfile:
                    outfile.write(new_content)
                print(f"       fixed line endings for {fp.name}")
