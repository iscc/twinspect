"""
MFND - MirFlickr Near-Duplicate Images

See: https://mfnd.similarity.eu/

Identical Near Duplicate Annotations:
    "http://www.mir-flickr-near-duplicates.appspot.com/truthFiles/IND_clusters.txt"

MIrFlickr Dataset
    Records: 1M Images
    Size: 117 GB (compressed)
    Info: https://press.liacs.nl/mirflickr/mirdownload.html

"""
import shutil
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Generator
from zipfile import ZipInfo
from loguru import logger as log
import httpx_cache as hc
from remotezip import RemoteZip
from rich.filesize import decimal
from twinspect import check_dir_fast
from twinspect.globals import progress
from twinspect.models import Dataset
from twinspect.options import opts
from rich.progress import Progress, TaskID


CLUSTERS = "http://www.mir-flickr-near-duplicates.appspot.com/truthFiles/IND_clusters.txt"
DL_TPL = "https://press.liacs.nl/mirflickr/mirflickr1m.v3b/images{}.zip"


def clusters() -> list[list[int]]:
    """Download and parse MirFlickr image ids clustered by near duplicates."""
    with hc.Client(cache=hc.FileCache(), always_cache=True) as client:
        response = client.get(CLUSTERS)

    cluster_ids = []
    for row in response.text.splitlines():
        ids = tuple(sorted(row.split()))
        cluster_ids.append(ids)

    return cluster_ids


def download_jobs(dataset):
    # type: (Dataset) -> Generator[tuple[str,ZipInfo,Path]]
    """
    Compile a list of download jobs.

    A Job is a tuple of:
        url: The URL to the zipfile that contains the image to be downloaded
        zinfo: The `ZipInfo` object containing the zip-relative path of the file to be downloaded
        cluster: The local path to the cluster folder for storing the image file
    """
    log.debug(f"Collecting download jobs for {dataset.name}")
    download_info = {i[0]: (i[1], i[2]) for i in image_ids()}
    seen_clusters = set()
    for cluster_id, cluster in enumerate(clusters()):
        cluster_path = dataset.data_folder / f"cluster_{int(cluster_id):05}"
        if cluster_path not in seen_clusters:
            cluster_path.mkdir(exist_ok=True, parents=True)
            seen_clusters.add(cluster_path)
        for image_id in cluster:
            url, zinfo = download_info[image_id]
            yield url, zinfo, cluster_path


def image_ids():
    # type: () -> Generator[tuple[str, str, ZipInfo]]
    """Yields image_id, zip_url, ZipInfo tuples for mapping image ids to inzip downloads paths."""
    log.debug("Collecting MirFlickr ZIP data")
    for zip_id in range(10):
        zip_url = DL_TPL.format(zip_id)
        with RemoteZip(zip_url) as zfile:
            for zinfo in zfile.infolist():
                if zinfo.filename.endswith(".jpg"):
                    image_id = Path(zinfo.filename).stem
                    yield image_id, zip_url, zinfo


def download_batch(zip_url, jobs, progress_, task_id, lock):
    # type: (str, list[tuple], Progress, TaskID, threading.Lock) -> int
    """Download a batch of image files and return number of processed files"""
    with RemoteZip(zip_url) as zfile:
        for zinfo, cluster_path in jobs:
            try:
                file_path = zfile.extract(zinfo.filename, cluster_path)
            except Exception as e:
                log.error(f"Failed to retrieve {zinfo.filename} - {e}")
                continue
            src = Path(file_path)
            dst = cluster_path
            with lock:
                # Move file, cleanup subfolders and update task
                progress_.update(task_id, advance=zinfo.file_size, refresh=True)
                try:
                    shutil.move(src, dst)
                    shutil.rmtree(src.parent.parent, ignore_errors=True)
                except Exception as e:
                    log.error(f"Failed move/cleanup {src} - {e}")
                    continue
            log.debug(f"Retrieved {Path(file_path).relative_to(opts.root_folder)}")
    return len(jobs)


def install(dataset):
    # type: (Dataset) -> Path
    # Check for existing data_folder
    if dataset.data_folder.exists():
        if dataset.checksum:
            check_dir_fast(dataset.data_folder, expected=dataset.checksum)
        log.debug(f"Using cached dataset {dataset.name}")
        return dataset.data_folder

    jobs = list(download_jobs(dataset))
    total_size = sum(j[1].file_size for j in jobs)
    human_size = decimal(total_size)
    log.debug(f"Download {len(jobs)} mirflickr image files {human_size}")

    # Organize jobs by zip_url for parellel download
    batches = defaultdict(list)
    for url, zinfo, cluster_path in jobs:
        batches[url].append((zinfo, cluster_path))

    # Download/Extract image files in parallel
    with progress:
        task_id = progress.add_task("download", name="Remote Zip Extraction", total=total_size)
        lock = threading.Lock()
        with ThreadPoolExecutor() as executor:
            futures = []
            for zip_url, jobs in batches.items():
                fut = executor.submit(download_batch, zip_url, jobs, progress, task_id, lock)
                futures.append(fut)
            for future in as_completed(futures):
                batch_size: int = future.result()
                log.debug(f"Finished batch of {batch_size} files")
