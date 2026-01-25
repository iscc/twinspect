# -*- coding: utf-8 -*-
"""Ensemble algorithm support for combining multiple simprints."""

import csv
from pathlib import Path
from loguru import logger as log
import twinspect as ts


__all__ = [
    "find_simprint_csv",
    "combine_simprints",
    "placeholder",
]


def placeholder(file_path):
    """Placeholder function for ensemble algorithms (not actually called)."""
    raise NotImplementedError("Ensemble algorithms combine existing simprints, not process files")


def find_simprint_csv(algo_label, dataset_label, checksum):
    # type: (str, str, str) -> Path | None
    """
    Find existing simprint CSV for a given algorithm, dataset, and checksum.

    Searches the data folder for an exact match using the checksum to avoid
    mixing simprints from different dataset versions.
    """
    expected_path = ts.opts.root_folder / f"{algo_label}-{dataset_label}-{checksum}-simprint.csv"
    if expected_path.exists():
        return expected_path
    return None


def combine_simprints(algo_labels, dataset_label, output_path):
    # type: (list[str], str, Path) -> Path
    """
    Combine multiple simprint CSVs into an ensemble simprint.

    Loads component simprint CSVs, verifies file alignment, concatenates codes
    via numpy, and writes combined CSV in standard format.

    :param algo_labels: List of component algorithm labels to combine.
    :param dataset_label: Dataset label to find matching simprints.
    :param output_path: Output path for the combined simprint CSV.
    :return: Path to the generated ensemble simprint CSV.
    :raises FileNotFoundError: If any component simprint CSV is missing.
    :raises ValueError: If component CSVs have misaligned files.
    """
    # Extract checksum from output_path to ensure we use matching component versions
    # Filename format: {algo_label}-{dataset_label}-{checksum}-simprint.csv
    parts = output_path.name.split("-")
    checksum = parts[2]  # third segment is the checksum

    component_data = []
    reference_files = None

    for algo_label in algo_labels:
        csv_path = find_simprint_csv(algo_label, dataset_label, checksum)
        if csv_path is None:
            raise FileNotFoundError(
                f"Simprint CSV not found for {algo_label}-{dataset_label}-{checksum}. "
                f"Run component benchmarks first or ensure ensemble benchmark "
                f"is defined after its components in config.yml. "
                f"Component simprints must match the current dataset checksum."
            )
        log.debug(f"Loading component simprint: {csv_path.name}")

        # Load CSV data
        rows = []
        with open(csv_path, "r", encoding="utf-8", newline="") as infile:
            reader = csv.DictReader(infile, delimiter=";")
            for row in reader:
                rows.append(row)

        # Extract files and codes
        files = [row["file"] for row in rows]
        codes = [row["code"] for row in rows]
        times = [int(row["time"]) for row in rows]

        # Verify file alignment
        if reference_files is None:
            reference_files = files
        elif files != reference_files:
            raise ValueError(
                f"File mismatch between component simprints. "
                f"Expected {len(reference_files)} files, got {len(files)} "
                f"or files are in different order."
            )

        component_data.append({"rows": rows, "codes": codes, "times": times})

    # Combine codes by concatenation
    num_files = len(reference_files)
    combined_rows = []

    for i in range(num_files):
        # Concatenate hex codes from all components
        combined_code = "".join(comp["codes"][i] for comp in component_data)
        # Sum times from all components
        combined_time = sum(comp["times"][i] for comp in component_data)

        # Use first component's metadata
        base_row = component_data[0]["rows"][i]
        combined_rows.append(
            {
                "id": base_row["id"],
                "code": combined_code,
                "file": base_row["file"],
                "size": base_row["size"],
                "time": combined_time,
            }
        )

    # Write combined CSV
    with open(output_path, "w", encoding="utf-8", newline="") as outf:
        writer = csv.writer(outf, delimiter=";")
        writer.writerow(["id", "code", "file", "size", "time"])
        for row in combined_rows:
            writer.writerow([row["id"], row["code"], row["file"], row["size"], row["time"]])

    log.info(f"Combined {len(algo_labels)} simprints into {output_path.name}")
    return output_path
