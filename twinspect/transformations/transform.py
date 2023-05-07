# -*- coding: utf-8 -*-
import os
from concurrent.futures import as_completed, ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional
from loguru import logger as log
from rich.progress import track
import twinspect as ts


__all__ = [
    "transform",
    "transform_data_folder",
]


def transform(file_path, label):
    # type: (Path, str) -> Optional[Path]
    """Transform file at file_path with Transformation"""
    ts_obj = ts.Transformation.from_label(label)
    try:
        result = ts_obj.apply(file_path)
    except Exception:
        return None
    return result


def transform_data_folder(data_folder, ts_labels):
    # type: (Path, List[str]) -> None
    """Parallel processing of transformations for a given data_foler"""
    cores = os.cpu_count()
    file_paths = list(ts.iter_original_files(data_folder))
    num_transforms = len(file_paths) * len(ts_labels)
    log.debug(f"Transforming {len(file_paths)} files in {data_folder}:")
    for ts_label in ts_labels:
        log.debug(f"  -> {ts.Transformation.from_label(ts_label).name}")
    log.debug(f"Applying {num_transforms} transformations with {cores} max workers")

    futures = []
    with ThreadPoolExecutor() as executor:
        # Sumbit tasks
        for ts_label in ts_labels:
            for fp in file_paths:
                futures.append(executor.submit(transform, fp, ts_label))
        # Collect results
        for future in track(
            as_completed(futures),
            description="Tranforming",
            console=ts.console,
            total=num_transforms,
        ):
            result = future.result()
            if result is None:
                log.error(f"Failed transformation")
            else:
                log.trace(f"-> {result.name}")
