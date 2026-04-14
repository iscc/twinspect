# -*- coding: utf-8 -*-
"""ISCC algorithm implementations for TwinSpect benchmarking."""

from typing import Optional
from pathlib import Path

import iscc_core as ic
import iscc_sdk as idk
from loguru import logger as log


def text_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_meta = False
    ic.core_opts.text_bits = 64
    try:
        iscc_meta = idk.code_text(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def image_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_meta = False
    ic.core_opts.image_bits = 64
    try:
        iscc_meta = idk.code_image(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def audio_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_meta = False
    ic.core_opts.audio_bits = 64
    try:
        iscc_meta = idk.code_audio(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def video_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_meta = False
    ic.core_opts.video_bits = 64
    try:
        iscc_meta = idk.code_video(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def image_code_s_64(fp) -> Optional[str]:
    """Generate 64-bit semantic image code using iscc-sci."""
    import iscc_sci as sci

    try:
        iscc_meta = sci.code_image_semantic(fp, bits=64)
        iscc_code = iscc_meta["iscc"]
        log.success(f"{iscc_code} <- {Path(fp).name}")
        code_obj = ic.Code(iscc_code)
        return code_obj.hash_bytes.hex()
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None


def text_code_s_64(fp) -> Optional[str]:
    """Generate 64-bit semantic text code via iscc-sdk (supports content extraction)."""
    import iscc_sdk as idk

    try:
        iscc_meta = idk.code_text_semantic(fp, bits=64)
        iscc_code = iscc_meta.iscc
        log.success(f"{iscc_code} <- {Path(fp).name}")
        code_obj = ic.Code(iscc_code)
        return code_obj.hash_bytes.hex()
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None
