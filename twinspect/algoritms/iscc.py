# -*- coding: utf-8 -*-
import iscc_core as ic
import iscc_sdk as idk


def audio_code(fp, bits) -> str:
    idk.sdk_opts.extract_metadata = False
    ic.core_opts.audio_bits = bits
    iscc_meta = idk.code_audio(fp)
    return iscc_meta.iscc_obj.hash_bytes.hex()

