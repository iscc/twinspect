"""Calculate groundtruth data"""
import csv
import sys
import time
from pathlib import Path
from typing import Callable, List, Tuple
import twinspect as ts
from loguru import logger as log
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from rich.progress import track

__all__ = [
    "load_groundtruth",
    "process_data_folder",
]


def load_groundtruth(dataset: ts.Dataset, algorithm: ts.Algorithm) -> Path:
    data_folder = data_folder = ts.opts.root_folder / dataset.label
    data_hash = ts.hash_folder(data_folder)

def process_file(function: Callable, task: ts.Task) -> ts.Task:
    start_time = time.perf_counter()
    task.code = function(task.file, 64)
    task.time = round((time.perf_counter() - start_time) * 1000)
    return task



def process_data_folder(data_folder: Path, function: Callable) -> Path:
    """Process all files in `data_folder` with `function`"""
    df_hash = ts.hash_folder(data_folder)
    result_path = data_folder.parent / f"{function.__name__}-{df_hash}.csv"
    data_folder = Path(data_folder)
    cores = os.cpu_count()
    total = ts.count_files(data_folder)
    log.debug(f"Processing {data_folder.name} with {cores} max workers")
    results = []
    with ProcessPoolExecutor(max_workers=cores) as executor:
        futures = []
        for idx, file_path in track(enumerate(ts.iter_files(data_folder)), total=total, description="Populating Tasks", console=ts.console):
            file_size = file_path.stat().st_size
            task = ts.Task(id=idx, file=file_path.as_posix(), size=file_size)
            futures.append(executor.submit(process_file, function, task))

        for future in track(as_completed(futures), description="Processing Files", console=ts.console, total=total, ):
            result = future.result()
            # Fix relative path
            result.file = Path(result.file).relative_to(data_folder).as_posix()
            log.trace(f"{result.code} <- {result.file}")
            data = result.dict().values()
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


if __name__ == '__main__':
    from twinspect.algoritms.iscc import audio_code
    process_data_folder(Path(r"E:\twinspect\fma_100"), audio_code)
