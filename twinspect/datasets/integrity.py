# -*- coding: utf-8 -*-
"""
A module for efficient integrity verification of files and folders.

To improve benchmark reproducibility we use integrity checks. Secure integrity verification is
computationally costly as it requires to compute cryptographic hashes for all files in a dataset.
To improve performance we support two kinds of integrity checks:

- **check_dir_fast**: a fast 64-bit black3 checksum generated from file metadata
- **check_dir_secure**: a secure 256-bit blake3 hash generated from file content

We compute hashes and verify integrity at various checkpoints during benchmark execution:

Compute and verify **secure** hash:
    - once after downloading a data collection

Compute and verify **fast** hash:
    - after building a clustered data folder
    - each time we construct a benchmark result file name
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator, Optional, Tuple
from blake3 import blake3
from loguru import logger as log
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    DownloadColumn,
)
from twinspect.exceptions import DuplicateFileError, EmptyFileError, IntegrityError
from twinspect import console

__all__ = [
    "check_dir_fast",
    "check_dir_secure",
    "hash_file_secure",
    "iter_file_meta",
]


def check_dir_fast(path, expected=None, raise_empty=True):
    # type: (str|Path, Optional[str], bool) -> str
    """
    Compute and return a fast 64-bit recursive directory checksum. Verify the result against the
    `expected` checksum if provided.

    The checksum is a 64-bit blake3 prefix computed recursively over the file metadata of an entire
    directory tree. The checksum is sensitive against changes of file order, names, sizes, and
    modification times.

    :param path: Path to folder for recursive checksum calculation.
    :param expected: Optional checksum to verify against.
    :param raise_empty: Raise error when encountering empty (0-bytes) files.
    :returns: Hex encoded calculated checksum
    :raises IntegrityError: If calculated checksum does not match the expected one.
    :raises EmptyFileError: If raise_empty is True, and we encounter a zero-byte file.
    """
    log.debug(f"Compute fast check: {path}, expected={expected}, raise_empty={raise_empty}")
    path = Path(path)
    hasher = blake3(max_threads=blake3.AUTO)
    for file, size, time in iter_file_meta(path):
        if size <= 0:
            if raise_empty:
                raise EmptyFileError(file)
            else:
                log.warning(f"Empty file {file}")
        ident = f"{file};{size};{time}".encode("utf-8")
        hasher.update(ident)
    actual_hash = hasher.hexdigest(8)
    if expected:
        if expected == actual_hash:
            log.info(f"Success verifying {path.name} against {expected}")
        else:
            raise IntegrityError(path, expected, actual_hash)
    else:
        log.warning(f"Add checksum {actual_hash} to {path.name} dataset configuration")

    return actual_hash


def check_dir_secure(path, expected=None, raise_dupes=True):
    # type: (str|Path, Optional[str], bool) -> str
    """
    Compute and return a secure 256-bit recursive directory hash. Verify the result against the
    `expected` hash if provided.

    The hash is a 256-bit blake3 computed recursively over the file content of an entire
    directory tree. The checksum is sensitive against changes of file ordering and content.

    :param path: Path to folder for recursive hash calculation.
    :param expected: Optional hash to verify against.
    :param raise_dupes: Raise error when encountering duplicate files.
    :returns: Hex encoded calculated hash
    :raises IntegrityError: If calculated hash does not match the expected one.
    :raises DuplicateFileError: If raise_dupes is True, and we encounter a duplicate file.
    """
    log.debug(f"Compute secure check: {path}, expected={expected}, raise_dupes={raise_dupes}")
    path = Path(path)
    file_paths_rel = []
    file_sizes = []

    for relpath, size, _ in iter_file_meta(path):
        file_paths_rel.append(relpath)
        file_sizes.append(size)

    file_sizes_dict = {rel_path: size for rel_path, size in zip(file_paths_rel, file_sizes)}
    hasher = blake3(max_threads=blake3.AUTO)

    total_size = sum(file_sizes)
    progress = Progress(
        TextColumn("[bold blue]Hashing {task.fields[dirname]}", justify="right"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task("Hashing", dirname=path.name, total=total_size)
        seen_files = {}
        cores = os.cpu_count()

        with ThreadPoolExecutor(cores * 4) as executor:
            # Submit hashing tasks
            hashing_futures = {
                executor.submit(hash_file_secure, path / rel_path): rel_path
                for rel_path in file_paths_rel
            }

            # Process completed hashing tasks
            for future in as_completed(hashing_futures):
                rel_path = hashing_futures[future]
                file_hash = future.result()

                if file_hash in seen_files:
                    if raise_dupes:
                        raise DuplicateFileError(rel_path, seen_files[file_hash])
                    else:
                        log.warning(f"Duplicate file {rel_path} == {seen_files[file_hash]}")

                seen_files[file_hash] = rel_path
                progress.update(task_id, advance=file_sizes_dict[rel_path], refresh=True)

        # Hash sorted file hashes
        for file_hash, _ in sorted(seen_files.items(), key=lambda x: x[1]):
            hasher.update(file_hash)

    dirhash = hasher.hexdigest()

    if expected:
        if expected == dirhash:
            log.info(f"Success verifying {path.name} against {expected}")
        else:
            raise IntegrityError(path, expected, dirhash)
    else:
        log.warning(f"Please add computed hash {dirhash} for dataset {path.name} to configuration.")
    return dirhash


def hash_file_secure(file_path):
    return blake3(file_path.read_bytes(), max_threads=blake3.AUTO).digest()


def iter_file_meta(path, root_path=None):
    # type: (str|Path, Optional[str|Path]) -> Iterator[Tuple[Path, int, float]]
    """
    Walk directory tree recursively with deterministic ordering and yield tuples of file metadata.

    Metadata = (relpath, size, mtime)

    - relpath: folder-relative pathlib.Path object
    - size: integer file size in number of bytes
    - mtime: float modification timestamp

    File-entries are yielded in reproducible and deterministic order (bottom-up). Symlincs are
    ignored silently.

    Implementation Note: We use os.scandir to reduce the number of syscalls for metadata collection.
    """
    root_path = Path(root_path or path)
    with os.scandir(path) as entries:
        # Sort the entries
        sorted_entries = sorted(entries, key=lambda e: e.name)

        # Separate directories and files
        dirs = [entry for entry in sorted_entries if entry.is_dir()]
        files = [entry for entry in sorted_entries if entry.is_file()]

        # Recursively process directories first (bottom-up traversal)
        for dir_entry in dirs:
            yield from iter_file_meta(Path(dir_entry.path), root_path=root_path)

        # Process files in the current directory
        for file_entry in files:
            relative_path = Path(file_entry).relative_to(root_path)
            file_size = file_entry.stat().st_size
            mtime = file_entry.stat().st_mtime
            yield relative_path, file_size, mtime
