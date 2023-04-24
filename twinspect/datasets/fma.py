import yaml

import twinspect as ts
import pathlib
from remotezip import RemoteZip
import random
from rich.progress import track


def install(dataset: ts.Dataset) -> pathlib.Path:
    """Install FMA Dataset"""

    # Create Cluster Folder
    cluster_folder = ts.opts.root_folder / dataset.label
    if cluster_folder.exists():
        return cluster_folder
    else:
        cluster_folder.mkdir()

    download_folder = download(dataset)
    ts.clusterize(download_folder, cluster_folder, dataset.clusters)
    transform(cluster_folder)
    return cluster_folder


def transform(cluster_folder: pathlib.Path):
    originals = list(ts.iter_original_files(cluster_folder))
    for fp in track(originals, description="FMA Transform"):
        for ts_obj in ts.cnf.transformations:
            if ts_obj.mode == ts.Mode.audio:
                ts_func = ts.load_function(ts_obj.function)
                ts_func(fp, *ts_obj.params)


def download(dataset: ts.Dataset) -> pathlib.Path:
    """Download FMA Dataset"""

    # Create Download folder
    download_folder = ts.opts.root_folder / f"downloads/{dataset.label}"
    if download_folder.exists():
        return download_folder
    else:
        download_folder.mkdir(parents=True)

    # Collect, download and extract samples
    audio_file_names = []
    with RemoteZip(dataset.url) as zipfile:
        # collect all names of audio files
        for file_name in zipfile.namelist():
            if file_name.endswith('.mp3'):
                audio_file_names.append(file_name)
        # Select samples
        random.seed(0)
        sample_file_names = random.sample(audio_file_names, dataset.samples)
        # Extract examples
        for sfn in track(sample_file_names, description="FMA Download"):
            zipfile.extract(sfn, download_folder)
    return download_folder


