# -*- coding: utf-8 -*-
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from loguru import logger as log
from pathlib import Path
from rich.progress import Progress
from twinspect.globals import console
from twinspect.tools import result_path
from twinspect.metrics.utils import update_json, get_metric, load_csv


def distribution(simprint_path, chunk_size=100):
    """Compute All-Pairs Hamming Distribution"""
    simprint_path = Path(simprint_path)
    algo, dataset, checksum = simprint_path.name.split("-")[:3]
    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result = get_metric(metrics_path, "distribution")

    if result:
        log.debug(f"Using cached [white on green]distribution[/] metric for {algo} -> {dataset}")
        do_update = False
    else:
        log.debug(f"Compute [white on red]distribution[/] metric for {algo} -> {dataset}")
        do_update = True
        simprints = load_csv(simprint_path)
        num_simprints = len(simprints)
        counter = Counter()
        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]Compute Distribution", total=num_simprints)
            # Compute hamming distances in chunks
            with ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(calculate_chunk, simprints, i, chunk_size)
                    for i in range(0, num_simprints, chunk_size)
                }
                for future in as_completed(futures):
                    chunk = future.result()
                    # Update the counter
                    counter.update(chunk.flatten())
                    progress.update(task, advance=chunk_size)
        result = {int(k): int(v) for k, v in sorted(counter.items())}

    # Store evaluation results
    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result = {
        "algorithm": algo,
        "dataset": dataset,
        "checksum": checksum,
        "metrics": {
            "distribution": result,
        },
    }
    if do_update:
        update_json(metrics_path, result)
    return result


def calculate_chunk(simprints, i, chunk_size):
    """Helper function to calculate a chunk of Hamming distances"""
    return np.unpackbits(simprints[i : i + chunk_size, None] ^ simprints, axis=2).sum(axis=2)
