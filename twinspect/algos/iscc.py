# -*- coding: utf-8 -*-
from typing import Optional
import iscc_core as ic
import iscc_sdk as idk


def image_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.image_bits = 64
    try:
        iscc_meta = idk.code_image(fp)
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def image_code_v0_256(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.image_bits = 256
    try:
        iscc_meta = idk.code_image(fp)
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def audio_code_v0_64(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.audio_bits = 64
    try:
        iscc_meta = idk.code_audio(fp)
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()


def audio_code_v0_256(fp) -> Optional[str]:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.audio_bits = 256
    try:
        iscc_meta = idk.code_audio(fp)
    except Exception:
        return None
    return iscc_meta.iscc_obj.hash_bytes.hex()
