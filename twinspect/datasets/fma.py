import csv
import io
import os
import shutil
import zipfile
import blake3
from codetiming import Timer
from pathlib import Path
from remotezip import RemoteZip
import random
from loguru import logger as log
from rich.progress import Progress
import twinspect as ts
from twinspect.datasets.integrity import check_dir_fast
from twinspect.datasets.ultils import clusterize
from twinspect.transformations.transform import transform_data_folder
from twinspect.models import Dataset
from twinspect.options import opts
from twinspect.tools import count_files
from twinspect.globals import console
from twinspect.datasets.integrity import hash_file_secure


def install(dataset):
    # type: (Dataset) -> Path
    """Install and transform a given FMA Dataset and return its data_folder"""
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
    ts_labels = [o.label for o in ts.Transformation.for_mode(dataset.mode)]

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
    audio_file_names = load_file_names(60)  # Minimum 60 seconds
    with RemoteZip(url) as zfile:
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
                file_path = zfile.extract(sfn, download_folder)
                log.debug(f"Retrieved {sfn}")
                file_hash = hash_file_secure(Path(file_path))
                if file_hash not in hashes:
                    hasher.update(file_hash)
                    hashes.add(file_hash)
                    counter += 1
                    prog.update(task, advance=1)
                    if counter == num_samples:
                        log.info(f"Downloaded {counter} files to {download_folder}")
                        break
                else:
                    log.warning(f"Delete duplicate file {Path(file_path).name}")
                    os.remove(file_path)
    return download_folder


def load_file_names(min_duration):
    # type: (int) -> list
    """Load file names from FMA-Large dataset filtered by minimum duration"""

    from twinspect.datasets.download import download_file

    # Cached download of metadata zip file
    fma_meta_url = "https://os.unil.cloud.switch.ch/fma/fma_metadata.zip"
    zip_file_path = download_file(fma_meta_url)

    log.debug(f"Loading FMA file names with {min_duration}s minimum duration")
    zip_obj = zipfile.ZipFile(zip_file_path)
    csv_file = "fma_metadata/tracks.csv"  # Track-ID = col 0 / Duration = col 38
    file_names = []
    with zip_obj.open(csv_file) as infile:
        text_stream = io.TextIOWrapper(infile, encoding="utf-8")
        reader = csv.reader(text_stream)
        skip = 3
        for _ in range(skip):
            next(reader)

        for row in reader:
            track_id, duration = row[0], row[38]
            if int(duration) >= min_duration:
                track_id = track_id.zfill(6)
                file_path = f"fma_full/{track_id[:3]}/{track_id}.mp3"
                file_names.append(file_path)
    return file_names
