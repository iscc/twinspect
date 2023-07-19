from pathlib import Path
import numpy as np
from twinspect.datasets.integrity import iter_file_meta, check_dir_fast
from twinspect.models import DatasetInfo
import iscc_sdk as idk
from loguru import logger as log


def dataset_info(data_folder):
    # type: (str|Path) -> DatasetInfo
    data_folder = Path(data_folder)
    log.debug(f"Collecting dataset information for {data_folder.name}")

    # Variables to store information
    total_size = 0
    total_files = 0
    clusters = {}
    transformations = set()
    dataset_mode = ""

    # Iterate over the files in the data folder
    for relpath, size, _ in iter_file_meta(data_folder):
        # Detect mode from first file only
        if total_files == 0:
            _, dataset_mode = idk.mediatype_and_mode((data_folder / relpath).as_posix())

        total_files += 1
        total_size += size

        # If the file is in a cluster
        if len(relpath.parts) > 1:
            cluster_name = relpath.parts[0]
            clusters.setdefault(cluster_name, []).append(relpath)

            # Check for transformations
            if "_" in relpath.name:
                transform = relpath.stem.split("_")[-1]
                transformations.add(transform)

    # Calculate cluster and distractor information
    cluster_sizes = [len(files) for files in clusters.values()]
    total_clusters = len(clusters)
    total_distractor_files = total_files - sum(cluster_sizes)

    # Calculate the ratio of cluster files to distractor files
    ratio_cluster_to_distractor = (
        (total_files - total_distractor_files) / total_distractor_files
        if total_distractor_files != 0
        else np.inf
    )

    # Calculate cluster size distribution
    cluster_sizes_distribution = {
        "min": min(cluster_sizes) if cluster_sizes else 0,
        "max": max(cluster_sizes) if cluster_sizes else 0,
        "mean": np.mean(cluster_sizes) if cluster_sizes else 0,
        "median": np.median(cluster_sizes) if cluster_sizes else 0,
    }

    # Calculate the checksum
    checksum = check_dir_fast(data_folder)

    # Return the dataset information
    result = {
        "dataset_label": data_folder.name,
        "dataset_mode": dataset_mode,
        "total_size": total_size,
        "total_files": total_files,
        "total_clusters": total_clusters,
        "cluster_sizes": cluster_sizes_distribution,
        "total_distractor_files": total_distractor_files,
        "ratio_cluster_to_distractor": ratio_cluster_to_distractor,
        "transformations": list(transformations),
        "checksum": checksum,
    }
    return DatasetInfo(**result)
