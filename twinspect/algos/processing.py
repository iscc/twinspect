"""Calculate ground truth data"""

import csv
import time
from pathlib import Path
from typing import Callable

from loguru import logger as log
from concurrent.futures import as_completed, ThreadPoolExecutor
import os
from rich.progress import track
from codetiming import Timer
import twinspect as ts


__all__ = [
    "simprint",
    "process_file",
    "process_data_folder",
    "benchmark_files",
]


def simprint(benchmark):
    # type: (ts.Benchmark) -> Path
    """
    Get file path to processed data for Dataset/Algorithm pair.

    Will either return a cached file path or generate a new one and return it.
    For ensemble algorithms, combines existing component simprints instead of
    processing files directly.
    """
    file_path = benchmark.filepath("csv", tag="simprint")
    if file_path.exists():
        log.debug(f"Using cached {file_path.name}")
        return file_path

    # Handle ensemble algorithms by combining component simprints
    if benchmark.algorithm.ensemble_of:
        from twinspect.algos.ensemble import combine_simprints

        return combine_simprints(
            algo_labels=benchmark.algorithm.ensemble_of,
            dataset_label=benchmark.dataset.label,
            output_path=file_path,
        )

    with Timer("Data-Folder Processing", text="{name}: {seconds:.2f} seconds", logger=log.info):
        path = process_data_folder(benchmark.algorithm.function, benchmark.dataset.data_folder)
    return path


def process_file(function: Callable, task: ts.Task) -> ts.Task:
    """
    Process compact code for a single media file.

    TODO: Collect essential metadata like duration, pixels, characters
    """
    start_time = time.perf_counter()
    task.code = function(task.file)
    task.time = round((time.perf_counter() - start_time) * 1000)
    return task


def benchmark_files(data_folder):
    # type: (Path) -> list[Path]
    """Return benchmark media inputs with deterministic ordering.

    Dataset-local metadata files are useful for reproducibility but are not media
    inputs. Skip top-level hidden/underscore metadata so simprint generation does
    not try to hash JSON build manifests.

    Directory-backed media formats, especially OME-NGFF/Zarr, must be treated as
    one benchmark input. Walking their internal chunk files would benchmark the
    container serialization instead of the decoded image content.
    """
    data_folder = Path(data_folder)

    def walk(path):
        entries = sorted(path.iterdir(), key=lambda item: item.name)
        for entry in entries:
            if entry.is_dir():
                if is_directory_media_input(entry):
                    yield entry
                else:
                    yield from walk(entry)
            elif not (entry.parent == data_folder and is_dataset_metadata_file(entry)):
                yield entry

    return list(walk(data_folder))


def is_directory_media_input(path):
    # type: (Path) -> bool
    """Return true for directory-backed media that should hash as one input."""
    return (
        path.suffix == ".zarr"
        or (path / ".zattrs").exists()
        or (path / "zarr.json").exists()
    )


def is_dataset_metadata_file(path):
    # type: (Path) -> bool
    """Return true for top-level dataset metadata that should not be hashed."""
    return path.name.startswith(".") or path.name == "_bioimage_convert_build.json"


def process_data_folder(func_path, data_folder):
    # type: (str, Path) -> Path
    """Process all files in `data_folder` with `function` and function `params`."""
    data_folder = Path(data_folder)
    result_path = ts.result_path(func_path, data_folder, extension="csv", tag="simprint")
    func = ts.load_function(func_path)
    cores = os.cpu_count()
    files = benchmark_files(data_folder)
    total = len(files)
    log.debug(f"Processing {data_folder.name} with {cores} max workers")
    results = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for idx, file_path in track(
            enumerate(files),
            total=total,
            description="Populating Tasks",
            console=ts.console,
        ):
            file_size = file_path.stat().st_size
            task = ts.Task(id=idx, file=file_path.as_posix(), size=file_size)
            futures.append(executor.submit(process_file, func, task))

        for future in track(
            as_completed(futures),
            description="Processing Files",
            console=ts.console,
            total=total,
        ):
            result = future.result()
            # Fix relative path
            result.file = Path(result.file).relative_to(data_folder).as_posix()
            if result.code is None:
                log.error(f"Failed {func.__name__} on {result.file}")
                continue
            results.append(result)

    # Sort results by index
    results = sorted(results, key=lambda obj: obj.id)
    with open(result_path, "wt", encoding="utf-8", newline="") as outf:
        writer = csv.writer(outf, delimiter=";")
        writer.writerow(["id", "code", "file", "size", "time"])
        for item in results:
            data = item.dict().values()
            writer.writerow(data)
    log.debug(f"Results stored in {result_path}")
    return result_path
