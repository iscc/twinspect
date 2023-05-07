import os
import shutil
import blake3
from codetiming import Timer
from pathlib import Path
from remotezip import RemoteZip
import random
from loguru import logger as log
from rich.progress import Progress
from twinspect.datasets.integrity import check_dir_fast
from twinspect.datasets.ultils import clusterize
from twinspect.transformations.transform import transform_data_folder
from twinspect.models import Transformation, Dataset
from twinspect.options import opts
from twinspect.tools import count_files
from twinspect.globals import console
from twinspect.datasets.integrity import hash_file_secure


def install(dataset):
    # type: (Dataset) -> Path
    """Install FMA Dataset and return data_folder"""
    # Check for existing data_folder
    if dataset.data_folder.exists():
        if dataset.checksum:
            check_dir_fast(dataset.data_folder, expected=dataset.checksum)
        log.debug(f"Using cached dataset {dataset.name}")
        return dataset.data_folder

    log.debug(f"Installing dataset {dataset.name}")
    # Download sample set from FMA FULL
    log.debug(f"Download {dataset.name}")
    download_folder = download_fma_samples(dataset.samples, dataset.seed, dataset.url)

    # Clusterize sample set from FMA FULL
    log.debug(f"Clusterize {dataset.name}")
    clusterize(download_folder, dataset.data_folder, dataset.clusters)

    # Apply file transformations on cluster originals
    log.debug(f"Transform {dataset.name}")
    ts_labels = [o.label for o in Transformation.for_mode(dataset.mode)]

    with Timer("Data-Folder Transform", text="{name}: {seconds:.2f} seconds", logger=log.info):
        transform_data_folder(dataset.data_folder, ts_labels)

    if dataset.checksum:
        check_dir_fast(dataset.data_folder, expected=dataset.checksum)
    else:
        checksum = check_dir_fast(dataset.data_folder)
        log.warning(f"Take note of checksum for {dataset.name} -> {checksum}")

    return dataset.data_folder


def download_fma_samples(num_samples, seed, url):
    # type: (int, int, str) -> Path
    """Download 'n' unique samples selected with 'seed' from FMA Full zip archive at 'url'"""
    # Re-use existing download folder if available
    download_folder = opts.root_folder / f"fma_temp_{num_samples}_{seed}"
    if download_folder.exists():
        num_files = count_files(download_folder)
        if num_files == num_samples:
            log.debug(f"Using cached download folder {download_folder} with {num_samples} files")
            return download_folder
        else:
            log.debug(f"Deleting existing but incomplete download folder {download_folder}")
            shutil.rmtree(download_folder)

    # Collect, download and extract samples
    download_folder.mkdir(parents=True)
    audio_file_names = []
    with RemoteZip(url) as zipfile:
        # collect all names of audio files
        for file_name in zipfile.namelist():
            if file_name.endswith(".mp3"):
                audio_file_names.append(file_name)
        # Select samples
        random.seed(seed)
        num_names = int(num_samples + (num_samples // 10))  # add 10% margin to filter dupes
        sample_file_names = random.sample(audio_file_names, num_names)

        # Extract examples
        hashes = set()
        hasher = blake3.blake3()
        counter = 0

        with Progress(console=console) as prog:
            task = prog.add_task(f"Dowloading {download_folder.name}", total=num_samples)
            for sfn in sample_file_names:
                file_path = zipfile.extract(sfn, download_folder)
                log.debug(f"Retrieved {sfn}")
                file_hash = hash_file_secure(Path(file_path))
                if file_hash not in hashes:
                    hasher.update(file_hash)
                    hashes.add(file_hash)
                    counter += 1
                    prog.update(task)
                    prog.refresh()
                    if counter == num_samples:
                        log.info(f"Downloaded {counter} files to {download_folder}")
                        break
                else:
                    log.warning(f"Delete duplicate file {Path(file_path).name}")
                    os.remove(file_path)
    return download_folder
