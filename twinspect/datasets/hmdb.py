from loguru import logger as log
import twinspect as ts
from pathlib import Path


def install(dataset):
    # type: (ts.Dataset) -> Path
    """Install HMDB dataset"""

    if dataset.data_folder.exists():
        if dataset.checksum:
            ts.check_dir_fast(dataset.data_folder, expected=dataset.checksum)
        log.debug(f"Using cached dataset {dataset.name}")
        return dataset.data_folder

    data_file = ts.download_file(dataset.url)
