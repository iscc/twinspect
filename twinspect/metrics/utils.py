import json
from pathlib import Path
from typing import Dict, Any
from loguru import logger as log

__all__ = ["update_json"]


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
    current_data.update(data)

    with json_path.open("w", newline="\n") as json_file:
        json.dump(current_data, json_file, indent=2)
