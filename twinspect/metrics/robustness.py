# -*- coding: utf-8 -*-
from pathlib import Path
from twinspect.metrics.eff import load_simprints
from hexhamming import hamming_distance_string as hamming_distance
import pandas as pd
from twinspect.tools import result_path
from twinspect.metrics.utils import update_json
from loguru import logger as log


def robustness(simprint_path):
    # type: (str|Path) -> dict
    """
    Calculate robustness against different transformations for simprint csv file.

    Take each original file and calculate hamming distances to all transformed versions in within
    the same clauster. Calculate min, max, mean, median hamming distances per transformation.

    The result is a dictionary of the form:

    {
        "robustness: [
            {
                "transform": "compressed-medium",
                "min": 1,
                "max": 3,
                "mean": 2.1,
                "median": 1.9,
            },
            ...
        ]
    }
    """
    simprint_path = Path(simprint_path)
    algo, dataset, checksum = simprint_path.name.split("-")[:3]
    log.debug(f"Compute [white on red]robustness[/]  for {algo} -> {dataset}")
    df_simprints = load_simprints(simprint_path)
    # Filter out the original files and group by cluster
    originals = df_simprints[df_simprints["is_original"]]
    grouped_transforms = df_simprints[~df_simprints["is_original"]].groupby("cluster")

    # Calculate hamming distances
    distances = []

    for _, original in originals.iterrows():
        cluster = original["cluster"]
        transformed_files = grouped_transforms.get_group(cluster)
        for _, transformed in transformed_files.iterrows():
            distance = hamming_distance(original["code"], transformed["code"])
            distances.append({"transform": transformed["transform"], "distance": distance})

    # Calculate min, max, mean, median distances per transformation
    df_distances = pd.DataFrame(distances)
    grouped_distances = df_distances.groupby("transform")
    stats = grouped_distances["distance"].agg(["min", "max", "mean", "median"]).reset_index()

    # Create the final result dictionary
    result = {"robustness": []}
    for _, row in stats.iterrows():
        result["robustness"].append(
            {
                "transform": row["transform"],
                "min": row["min"],
                "max": row["max"],
                "mean": row["mean"],
                "median": row["median"],
            }
        )

    # Store evaluaion results
    metrics_path = result_path(algo, dataset, "json", tag="metrics")
    result = {
        "algorithm": algo,
        "dataset": dataset,
        "checksum": checksum,
        "metrics": {
            "robustness": result["robustness"],
        },
    }
    update_json(metrics_path, result)

    return result
