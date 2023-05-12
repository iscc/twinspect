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
]


def simprint(benchmark):
    # type: (ts.Benchmark) -> Path
    """
    Get file path to processed data for Dataset/Algorithm pair.

    Will either return a cached file path or generate a new one and return it.
    """
    file_path = benchmark.filepath("csv", tag="simprint")
    if file_path.exists():
        log.debug(f"Using cached {file_path.name}")
        return file_path
    with Timer("Data-Folder Processing", text="{name}: {seconds:.2f} seconds", logger=log.info):
        path = process_data_folder(benchmark.algorithm.function, benchmark.dataset.data_folder)
    return path


def process_file(function, task):
    # type: (Callable, ts.Task) -> ts.Task
    """
    Process compact code for a single media file.

    TODO: Collect essential metadata like duration, pixels, characters
    """
    start_time = time.perf_counter()
    task.code = function(task.file)
    task.time = round((time.perf_counter() - start_time) * 1000)
    return task


def process_data_folder(func_path, data_folder):
    # type: (str, Path) -> Path
    """Process all files in `data_folder` with `function` and function `params`."""
    data_folder = Path(data_folder)
    result_path = ts.result_path(func_path, data_folder, extension="csv", tag="simprint")
    func = ts.load_function(func_path)
    cores = os.cpu_count()
    total = ts.count_files(data_folder)
    log.debug(f"Processing {data_folder.name} with {cores} max workers")
    results = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for idx, file_path in track(
            enumerate(ts.iter_files(data_folder)),
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
