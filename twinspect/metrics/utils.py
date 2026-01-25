import csv
import json
from pathlib import Path
from typing import Dict, Any
import jmespath
import numpy as np
from numpy.typing import NDArray
from loguru import logger as log


def load_csv(simprint_path, code_field="code"):
    # type: (str|Path, str) -> NDArray[np.uint8]
    """Load simprints to numpy uint8 matrix."""
    simprint_path = Path(simprint_path)
    log.debug(f"Loading codes from {simprint_path.name}")
    with simprint_path.open("r") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        hex_codes = [row[code_field] for row in reader]
    num_codes = len(hex_codes)
    code_length = len(hex_codes[0]) // 2
    uint8_matrix = np.empty((num_codes, code_length), dtype=np.uint8)
    for i, hex_code in enumerate(hex_codes):
        for j in range(0, len(hex_code), 2):
            uint8_matrix[i, j // 2] = np.uint8(int(hex_code[j : j + 2], 16))
    log.debug(f"Loaded {len(uint8_matrix)} simprints to numpy")
    return uint8_matrix


def load_csv_with_clusters(simprint_path, code_field="code", file_field="file"):
    # type: (str|Path, str, str) -> tuple[NDArray[np.uint8], NDArray[np.int32]]
    """Load simprints with cluster membership information.

    Returns a tuple of (codes, clusters) where:
    - codes: numpy uint8 matrix of binary codes
    - clusters: numpy int32 array mapping each file to a cluster index (-1 for no cluster)
    """
    simprint_path = Path(simprint_path)
    log.debug(f"Loading codes with clusters from {simprint_path.name}")

    with simprint_path.open("r") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        rows = list(reader)

    hex_codes = [row[code_field] for row in rows]
    file_paths = [row[file_field] for row in rows]

    # Extract cluster from file path (first segment before '/')
    cluster_names = []
    for fp in file_paths:
        if "/" in fp:
            cluster_names.append(fp.split("/")[0])
        else:
            cluster_names.append(None)

    # Map cluster names to numeric indices
    unique_clusters = {}
    cluster_indices = []
    for name in cluster_names:
        if name is None:
            cluster_indices.append(-1)
        else:
            if name not in unique_clusters:
                unique_clusters[name] = len(unique_clusters)
            cluster_indices.append(unique_clusters[name])

    # Build codes matrix
    num_codes = len(hex_codes)
    code_length = len(hex_codes[0]) // 2
    uint8_matrix = np.empty((num_codes, code_length), dtype=np.uint8)
    for i, hex_code in enumerate(hex_codes):
        for j in range(0, len(hex_code), 2):
            uint8_matrix[i, j // 2] = np.uint8(int(hex_code[j : j + 2], 16))

    clusters_array = np.array(cluster_indices, dtype=np.int32)
    log.debug(f"Loaded {num_codes} simprints with {len(unique_clusters)} clusters")
    return uint8_matrix, clusters_array


def get_metric(metrics_path, metric):
    # type: (str|Path, str) -> dict|None
    """Return a given metric from metrics file path."""
    metrics_path = Path(metrics_path)
    if not metrics_path.exists():
        return None

    with metrics_path.open("r") as json_file:
        data = json.load(json_file)

    if "metrics" not in data:
        return None

    return data["metrics"].get(metric, None)


def update_json(json_file_path: str | Path, data: Dict[str, Any]) -> None:
    """
    Update a JSON file with the data from the provided dictionary.
    If the JSON file does not exist, it creates a new one.

    :param json_file_path: The path to the JSON file to update.
    :param data: A dictionary containing the data to update the JSON file with.
    """
    json_path = Path(json_file_path)

    if json_path.exists():
        log.debug(f"Loading {json_path.name}")
        with json_path.open("r") as json_file:
            current_data = json.load(json_file)
    else:
        log.debug(f"Creating {json_path.name}")
        current_data = {}

    metric = list(data["metrics"].keys())[0]
    log.debug(f"Updating {json_path.name} with {metric}-metric")
    current_data = update_nested_dict(current_data, data)

    with json_path.open("w", newline="\n") as json_file:
        json.dump(current_data, json_file, indent=2)


def best_threshold(metrics):
    # type: (dict) -> None|dict
    """Find effectivness metric with best f1-score"""
    find_best_f1 = "metrics.effectiveness | max_by(@, &f1_score)"
    best_f1 = jmespath.search(find_best_f1, metrics)
    return best_f1


def update_nested_dict(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively update dictionary d with values from dictionary u.

    :param d: The dictionary to update.
    :param u: The dictionary containing the new values.
    :return: The updated dictionary.
    """
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = update_nested_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d
