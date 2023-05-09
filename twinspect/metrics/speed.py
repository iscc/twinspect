"""Metrics for algorithm execition speed"""
from pathlib import Path
import csv
from statistics import mean, median
from twinspect.tools import result_path
from twinspect.metrics.utils import update_json
from loguru import logger as log


def speed(simprint_path):
    # type: (Path) -> dict
    """Calculate execution speed from simprint csv file"""
    simprint_path = Path(simprint_path)
    algo, dataset, checksum = simprint_path.name.split("-")[:3]
    log.debug(f"Compute [white on red]speed[/] for {algo} -> {dataset}")

    with open(simprint_path, "r") as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=";")
        bpms = []  # bytes per millisecond

        for row in csvreader:
            size = int(row["size"])
            time = int(row["time"])
            bpm = size / time
            bpms.append(bpm)

        result = {"min": min(bpms), "max": max(bpms), "mean": mean(bpms), "median": median(bpms)}

    readable = {}
    for key, value in result.items():
        bytes_per_sec = value * 1000  # Convert bytes/ms to bytes/s
        mb_per_sec = bytes_per_sec / 1_000_000  # Convert bytes/s to MB/s
        human_readable_value = f"{mb_per_sec:.2f}"
        readable[f"{key}_human"] = f"{human_readable_value} MB/s"

    result.update(readable)

    # Store result
    algo, dataset, checksum = simprint_path.name.split("-")[:3]

    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result = {
        "algorithm": algo,
        "dataset": dataset,
        "checksum": checksum,
        "metrics": {
            "speed": result,
        },
    }
    update_json(metrics_path, result)

    return result
