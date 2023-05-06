"""Specialized dataset download functions."""
import random
import threading
from concurrent.futures import as_completed, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
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
from httpx import Client, HTTPError
from urllib.parse import urlparse


__all__ = [
    "download_multi",
    "download_samples",
]


def download_multi(urls, target=None, workers=cpu_count(), dedupe=False):
    # type: (list[str], Path|None, int|None, bool|None) -> None
    """Download files from multiple urls in parallel while showing a progress bar.

    Note: web servers must support head requests and return content-length headers

    :param urls: List of urls to download files from.
    :param target: The directory to save the files to. If None, a temporary directory is created.
    :param workers: The number of threads to use for downloading. Default: number of CPUs.
    :param dedupe: Skip downloads with duplicate content (based on ETags). Default: False
    """
    # Dedupe duplicate urls (not duplicate content)
    num_urls_orig = len(urls)
    urls = list(set(urls))
    num_urls_dedup = len(urls)
    if num_urls_orig != num_urls_dedup:
        log.warning(f"Removed {num_urls_orig - num_urls_dedup} duplicate urls")

    content_ids = {}  # Maps ETags to URLs

    # Collect file metadata (FileInfo) and filter urls
    with ThreadPoolExecutor(max_workers=workers) as pool:
        with Client() as client:
            func = partial(get_info, client=client)
            file_infos = []
            log.debug(f"Collect file infos for {len(urls)} urls with {workers} workers.")
            for file_info in pool.map(func, urls):
                file_info: FileInfo
                if dedupe and file_info.etag in content_ids:
                    log.debug(f"Skipped duplicate {file_info.url} == {content_ids[file_info.etag]}")
                    continue
                if not file_info.size:
                    log.warning(f"No conent-length for {file_info}")
                file_infos.append(file_info)

    total_size = sum(fi.size for fi in file_infos if fi.size)
    human_size = decimal(total_size)
    good_urls = [fi.url for fi in file_infos]
    filename_size = {fi.url.split("/")[-1]: fi.size for fi in file_infos}
    target = target or Path(tempfile.mkdtemp())
    counter = 0
    log.debug(f"Download {len(file_infos)} files ({human_size}) with {workers} workers")
    with progress:
        task_id = progress.add_task("download", name="Downloading", total=total_size)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            with Client() as client:
                func = partial(download_file, target=target, client=client)
                for file_path in pool.map(func, good_urls):
                    if file_path:
                        counter += 1
                        log.debug(f"Retrieved {file_path.name}")
                        progress.update(
                            task_id, advance=filename_size[file_path.name], refresh=True
                        )
    log.debug(f"Downloded {counter} files to {target}")


def download_file(url, target=None, client=None):
    # type: (str, Path|None, Client|None) -> Path|None
    """
    Download a file from the given URL to the target directory and return the file path.

    :param url: The URL of the file to download.
    :param target: The directory to save the file to. If None, a temporary directory is created.
    :param client: The HTTPX client to use for downloading. If None, a new client is created.
    :return: The path of the downloaded file or None if an error occurs during the download process.
    """
    filename = urlparse(url).path.split("/")[-1]
    target = target or Path(tempfile.mkdtemp())
    filepath = Path(target) / filename
    client = client or Client()
    with open(filepath, "wb") as outfile:
        try:
            with client.stream("GET", url) as instream:
                for chunk in instream.iter_bytes():
                    outfile.write(chunk)
        except HTTPError as e:
            log.error(repr(e))
            return None
    return filepath


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


def zip_download_worker(url, samples, target, progress_, task_id, lock):
    # type: (str, list[ZipInfo], Path, Progress, TaskID, threading.Lock) -> int
    """A worker thread for download of multiple members from a remote zip archive.

    :param url: The URL of the remote zip file.
    :param samples: List of ZipInfo objects representing the samples to be downloaded.
    :param target: The target directory where the samples will be saved.
    :param progress_: The progress object to update the progress bar.
    :param task_id: The task ID associated with the progress object.
    :param lock: The lock object to synchronize access to the progress object.
    :return: The number of downloaded samples.
    """
    with RemoteZip(url) as zipfile:
        for zinfo in samples:
            zipfile.extract(zinfo, target)
            log.debug(f"Retrieved {zinfo.filename}")
            with lock:
                progress_.update(task_id, advance=zinfo.file_size, refresh=True)
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


@dataclass
class FileInfo:
    url: str
    type: str | None = None
    size: int | None = None
    etag: str | None = None
    status: int | None = None


def get_info(url, client=None):
    # type: (str, Client|None) -> FileInfo|None
    """Get file information for url via head request"""
    if client:
        try:
            response = client.head(url)
            response.raise_for_status()
        except HTTPError as e:
            log.error(repr(e))
            return FileInfo(url, status=e.response.status_code)
    else:
        with Client() as c:
            try:
                response = c.head(url)
                response.raise_for_status()
            except HTTPError as e:
                log.error(repr(e))
                return FileInfo(url, status=e.response.status_code)

    return FileInfo(
        url=str(response.url),
        type=response.headers.get("content-type"),
        size=int(response.headers.get("content-length")),
        etag=response.headers.get("etag"),
        status=response.status_code,
    )
