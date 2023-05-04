"""Specialized dataset download functions."""
import random
import threading
from concurrent.futures import as_completed, ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from zipfile import ZipInfo
from loguru import logger as log
from remotezip import RemoteZip
from twinspect.globals import progress
from os import cpu_count
from more_itertools import chunked_even
from rich.filesize import decimal
from rich.progress import Progress, TaskID
import tempfile

__all__ = ["download_samples"]


def download_samples(url, num_samples, target=None, filter_=None, seed=0):
    # type: (str, int, Path|None, str|None, int) -> Path
    """Download a number of random samples from a remote zip file in parallel with progress bar.

    :param url: The URL of the remote zip file.
    :param num_samples: The number of random samples to select and download.
    :param target: The target directory where the samples will be saved. Default is ./download.
    :param filter_: A string to filter the filenames in the zip file. Default is None.
    :param seed: An integer seed for initializing the selection of random samples. Defauls is 0.
    :return: Path to target download directory.
    """
    if target is None:
        target = Path(tempfile.mktemp())  # Set default target directory

    log.debug(f"Download samples from {url} -> {target.absolute().as_posix()}")

    samples = zip_samples(url, num_samples, filter_=filter_, seed=seed)
    zip_download(url, samples, target)
    return target


def zip_download(url, files, target, workers=cpu_count()):
    # type: (str, list[ZipInfo], Path, int) -> None
    """
    Download individual files from a zip archive without downloading the full content.

    :param url: The URL of the remote zip file.
    :param files: List of ZipInfo objects representing the samples to be downloaded.
    :param target: The target directory where the samples will be saved.
    :param workers: The number of threads to use for downloading. Default: number of CPUs.
    """
    total_size = sum(info.file_size for info in files)
    human_size = decimal(total_size)
    log.debug(f"Download {len(files)} files ({human_size}) with {workers} workers")
    with progress:
        task_id = progress.add_task("download", name="Remote Zip Extraction", total=total_size)
        lock = threading.Lock()
        with ThreadPoolExecutor() as executor:
            sample_batches = chunked_even(files, workers)
            futures = []
            for batch in sample_batches:
                fut = executor.submit(
                    zip_download_worker, url, batch, target, progress, task_id, lock
                )
                futures.append(fut)
            for future in as_completed(futures):
                batch_size: int = future.result()
                log.debug(f"Finished batch of {batch_size} files")


def zip_download_worker(url, samples, target, progress, task_id, lock):
    # type: (str, list[ZipInfo], Path, Progress, TaskID, threading.Lock) -> int
    """A worker thread for download of multiple members from a remote zip archive.

    :param url: The URL of the remote zip file.
    :param samples: List of ZipInfo objects representing the samples to be downloaded.
    :param target: The target directory where the samples will be saved.
    :param progress: The progress object to update the progress bar.
    :param task_id: The task ID associated with the progress object.
    :param lock: The lock object to synchronize access to the progress object.
    :return: The number of downloaded samples.
    """
    with RemoteZip(url) as zipfile:
        for zinfo in samples:
            zipfile.extract(zinfo, target)
            log.debug(f"Retrieved {zinfo.filename}")
            with lock:
                progress.update(task_id, advance=zinfo.file_size, refresh=True)
    return len(samples)


def zip_samples(url, num_samples, filter_=None, seed=0):
    # type: (str, int, str|None, int) -> list[ZipInfo]
    """
    Select a number of random samples from a remote zip file sorted by filename.

    :param url: The URL of the remote zip file.
    :param num_samples: The number of random samples to select.
    :param filter_: A string to filter the filenames in the zip file. Default is None.
    :param seed: The seed for random sample selection to ensure reproducibility. Default is 0.
    :return: A list of ZipInfo objects representing the selected random samples.
    """

    with RemoteZip(url) as zipfile:
        zip_infos = zipfile.infolist()

    if filter_:
        zip_infos = [zi for zi in zip_infos if filter_ in zi.filename]

    zip_infos = sorted(zip_infos, key=lambda info: info.filename)

    with random_seed(seed):
        samples = random.sample(zip_infos, num_samples)

    return samples


@contextmanager
def random_seed(seed):
    # type: (int) -> None
    """
    Context manager for setting the random seed temporarily.

    :param seed: The seed value to use for random number generation.
    """
    old_state = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(old_state)
