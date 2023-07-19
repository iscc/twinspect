# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional
from PIL import Image
import imagehash
from loguru import logger as log


def ih_phash_64(fp) -> Optional[str]:
    try:
        hash_ = imagehash.phash(Image.open(fp))
        log.success(f"{hash_} <- {Path(fp).name}")
    except Exception:
        return None
    return str(hash_)


def ih_phash_256(fp) -> Optional[str]:
    try:
        hash_ = imagehash.phash(Image.open(fp), hash_size=16)
        log.success(f"{hash_} <- {Path(fp).name}")
    except Exception:
        return None
    return str(hash_)


def ih_wavelet_64(fp) -> Optional[str]:
    try:
        hash_ = imagehash.dhash(Image.open(fp))
        log.success(f"{hash_} <- {Path(fp).name}")
    except Exception:
        return None
    return str(hash_)
