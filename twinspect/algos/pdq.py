"""Facebool PDQ Hash"""
import warnings
from pathlib import Path


warnings.filterwarnings("ignore", category=UserWarning)
from typing import Optional
import cv2
import pdqhash
from loguru import logger as log


def pdq_hash_64(fp) -> Optional[str]:
    fp = Path(fp)
    try:
        image = cv2.imread(fp.as_posix())
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        hash_vector, quality = pdqhash.compute(image)
        hash_vector = hash_vector[::4]
        binary_str = "".join(map(str, hash_vector.flatten()))
        binary_int = int(binary_str, 2)
        hex_str = hex(binary_int)[2:]
        hex_str = hex_str.zfill(16)
        log.success(f"{hex_str} <- {fp.name}")
    except Exception as e:
        log.error(f"Error hashing {fp.name}")
        return None
    return hex_str


if __name__ == "__main__":
    f = r"E:\twinspect\mirflickr_mfnd\cluster_00000\939200.jpg"
    print(pdq_hash_64(f))
