# -*- coding: utf-8 -*-
from typing import Optional
import iscc_core as ic
import iscc_sdk as idk
from loguru import logger as log
from pathlib import Path


def image_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.image_bits = 64
    try:
        iscc_meta = idk.code_image(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def image_code_v0_256(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.image_bits = 256
    try:
        iscc_meta = idk.code_image(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def audio_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.audio_bits = 64
    try:
        iscc_meta = idk.code_audio(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def audio_code_v0_256(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.audio_bits = 256
    try:
        iscc_meta = idk.code_audio(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def iscc_code_v0_128(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.image_bits = 64
    ic.core_opts.audio_bits = 64
    ic.core_opts.text_bits = 64
    ic.core_opts.video_bits = 64
    try:
        iscc_meta = idk.code_iscc(fp)
        log.success(f"{iscc_meta.iscc} <- {Path(fp).name}")
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()[16:-16]
