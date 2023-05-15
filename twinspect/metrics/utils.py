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
    """Load simprints to numpy uint8 matrix"""
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
