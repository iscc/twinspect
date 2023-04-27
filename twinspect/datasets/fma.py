import os
import shutil
from concurrent.futures import ProcessPoolExecutor
import blake3
import twinspect as ts
from pathlib import Path
from remotezip import RemoteZip
import random
from loguru import logger as log
from rich.progress import track


def install(dataset: ts.Dataset) -> Path:
    """Install FMA Dataset"""
    data_folder = clusterize(dataset)
    return data_folder


def process_transformation(tansform):
    ts_obj, target_file = tansform
    ts_func = ts.load_function(ts_obj.function)
    if ts_obj.params:
        ts_func(target_file, *ts_obj.params)
    else:
        ts_func(target_file)


def clusterize(dataset: ts.Dataset) -> Path:
    """Create data folder with clustered transformations"""

    download_folder = download(dataset)
    data_folder = ts.opts.root_folder / dataset.label
    # Use cached data folder  if available
    if data_folder.exists():
        if dataset.data_hash:
            ts.check_folder(data_folder, dataset.data_hash)
        log.debug(f"Using cached data folder {data_folder}")
        return data_folder

    # Process raw data to data folder
    clusters = dataset.clusters
    clustered = 0
    audio_files = [p for p in download_folder.rglob("*") if p.is_file()]
    ts_objects = [tf for tf in ts.cnf.transformations if tf.mode == ts.Mode.audio]
    log.debug(f"Processing {dataset.clusters} files from {dataset.name} with {len(ts_objects)} transformations:")
    for ts_obj in ts_objects:
        log.debug(f"Transform: {ts_obj.name}")
    for path in track(audio_files, description=f"Processing {dataset.name}", console=ts.console):
        if clustered < clusters:
            cluster_folder_name = f"{clustered:07d}"
            target_dir = data_folder / cluster_folder_name
            target_dir.mkdir(parents=True)
            target_file = target_dir / f"0{path.name}"
            shutil.copy(path, target_file)
            clustered += 1
            # Process transformations in parallel
            transforms = [(tf, target_file) for tf in ts_objects]
            with ProcessPoolExecutor() as excecutor:
                log.debug(f"Transforming {path.name}")
                excecutor.map(process_transformation, transforms)
        else:
            shutil.copy(path, data_folder)

    data_hash = ts.hash_folder(data_folder)
    log.info(f"Dataset {dataset.name} data_hash: {data_hash}")
    return data_folder


def download(dataset: ts.Dataset) -> Path:
    """Download FMA Dataset and return download folder"""
    # Use cached download folder if available
    download_folder = ts.opts.root_folder / f"downloads/{dataset.label}"
    if download_folder.exists():
        if dataset.download_hash:
            ts.check_folder(download_folder, dataset.download_hash)
        log.debug(f"Using cached download folder {download_folder}")
        return download_folder

    # Collect, download and extract samples
    download_folder.mkdir(parents=True)
    audio_file_names = []
    with RemoteZip(dataset.url) as zipfile:
        # collect all names of audio files
        for file_name in zipfile.namelist():
            if file_name.endswith('.mp3'):
                audio_file_names.append(file_name)
        # Select samples
        random.seed(dataset.seed)
        num_samples = int(dataset.samples + (dataset.samples // 10))  # add 10% to filter dupes
        sample_file_names = random.sample(audio_file_names, num_samples)

        # Extract examples
        hashes = set()
        hasher = blake3.blake3()
        counter = 0
        for sfn in track(sample_file_names, description=f"Download {dataset.name}", console=ts.console):
            log.debug(f"Downloading {sfn}")
            file_path = zipfile.extract(sfn, download_folder)
            file_hash = ts.hash_file(Path(file_path))
            if file_hash not in hashes:
                hasher.update(file_hash)
                hashes.add(file_hash)
                counter += 1
                if counter == dataset.samples:
                    log.info(f"Downloaded {dataset.samples} files for {dataset.name}")
                    break
            else:
                log.warning(f"Delete duplicate file {Path(file_path).name}")
                os.remove(file_path)
    dl_hash = ts.hash_folder(download_folder)
    log.info(f"Dataset {dataset.name} download_hash: {dl_hash}")
    return download_folder
