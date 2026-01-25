# -*- coding: utf-8 -*-
"""Compute hamming distance distributions separated by cluster membership.

This module computes two separate distance distributions:
- intra: distances between files in the same cluster (ground truth positives)
- inter: distances between files in different clusters (ground truth negatives)

This separation allows visualization of algorithm effectiveness - a good algorithm
should show clear separation between intra-cluster (low distance) and inter-cluster
(high distance) distributions.
"""

from collections import Counter
import numpy as np
from loguru import logger as log
from pathlib import Path
from rich.progress import Progress
from twinspect.globals import console
from twinspect.tools import result_path
from twinspect.metrics.utils import update_json, get_metric, load_csv_with_clusters


def distribution(simprint_path, chunk_size=100):
    """Compute intra-cluster and inter-cluster hamming distance distributions."""
    simprint_path = Path(simprint_path)
    algo, dataset, checksum = simprint_path.name.split("-")[:3]
    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result = get_metric(metrics_path, "distribution")

    # Check if cached result has new format (with intra/inter keys)
    if result and "intra" in result:
        log.debug(f"Using cached [white on green]distribution[/] metric for {algo} -> {dataset}")
        do_update = False
    else:
        log.debug(f"Compute [white on red]distribution[/] metric for {algo} -> {dataset}")
        do_update = True
        simprints, clusters = load_csv_with_clusters(simprint_path)
        result = compute_distributions(simprints, clusters, chunk_size)

    # Store evaluation results
    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result_obj = {
        "algorithm": algo,
        "dataset": dataset,
        "checksum": checksum,
        "metrics": {
            "distribution": result,
        },
    }
    if do_update:
        update_json(metrics_path, result_obj)
    return result_obj


def compute_distributions(simprints, clusters, chunk_size=100):
    """Compute separate intra-cluster and inter-cluster distance distributions.

    Uses upper triangle only (excluding diagonal) to avoid double-counting pairs.
    """
    num_simprints = len(simprints)
    intra_counter = Counter()
    inter_counter = Counter()

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Compute Distribution", total=num_simprints)

        for i in range(num_simprints):
            # Compute distances from file i to all files j > i (upper triangle)
            if i + 1 >= num_simprints:
                progress.update(task, advance=1)
                continue

            # Get distances from i to all j > i
            remaining = simprints[i + 1 :]
            distances = compute_hamming_distances(simprints[i], remaining)

            # Determine which pairs are intra-cluster vs inter-cluster
            cluster_i = clusters[i]
            remaining_clusters = clusters[i + 1 :]

            # Intra-cluster: same cluster AND cluster is valid (not -1)
            if cluster_i >= 0:
                intra_mask = remaining_clusters == cluster_i
                intra_distances = distances[intra_mask]
                intra_counter.update(intra_distances)

                inter_mask = ~intra_mask
                inter_distances = distances[inter_mask]
                inter_counter.update(inter_distances)
            else:
                # File i has no cluster - all pairs are inter-cluster
                inter_counter.update(distances)

            progress.update(task, advance=1)

    # Convert counters to sorted dicts with int keys/values
    intra_result = {int(k): int(v) for k, v in sorted(intra_counter.items())}
    inter_result = {int(k): int(v) for k, v in sorted(inter_counter.items())}

    log.debug(
        f"Distribution computed: {sum(intra_counter.values())} intra-cluster pairs, "
        f"{sum(inter_counter.values())} inter-cluster pairs"
    )

    return {"intra": intra_result, "inter": inter_result}


def compute_hamming_distances(code, codes):
    """Compute hamming distances between a single code and multiple codes.

    Returns an array of hamming distances (popcount of XOR).
    """
    xor_result = np.bitwise_xor(code, codes)
    return np.unpackbits(xor_result, axis=1).sum(axis=1)
