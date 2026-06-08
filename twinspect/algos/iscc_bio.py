# -*- coding: utf-8 -*-
"""ISCC-BIO algorithm implementations for TwinSpect benchmarking."""

from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger as log
_LAZY_BIOFORMATS_PATCHED = False


def _patch_lazy_bioformats_planes():
    """Make current iscc-bio tolerate Bio-Formats LazyBioArray planes.

    Some BioIO/Bio-Formats readers return a LazyBioArray from ``compute()``. The
    installed iscc-bio version assumes a NumPy ndarray and calls ``flatten``
    directly, which prevents DICOM/ICS/IDS default-conversion targets from being
    benchmarked. Coercing to ndarray preserves the same canonical pixel bytes for
    ordinary arrays and lets Bio-Formats-backed planes hash normally.
    """
    global _LAZY_BIOFORMATS_PATCHED
    try:
        import iscc_bio.biocode as biocode_module
        import iscc_bio.imagewalk.common as common
    except ImportError:
        return

    if _LAZY_BIOFORMATS_PATCHED:
        return

    original = common.plane_to_canonical_bytes

    def plane_to_canonical_bytes(plane):
        return original(np.asarray(plane))

    common.plane_to_canonical_bytes = plane_to_canonical_bytes
    biocode_module.plane_to_canonical_bytes = plane_to_canonical_bytes
    _LAZY_BIOFORMATS_PATCHED = True


def bioimage_data_code_iw_64(fp) -> Optional[str]:
    # type: (str | Path) -> Optional[str]
    """Generate a 64-bit IMAGEWALK-based bioimage Data-Code via ``iscc-bio``.

    ``iscc-bio`` decodes bioimage formats with IMAGEWALK/BioIO and hashes canonical
    plane pixels. That is the unit we want for same-image/different-format matching,
    not a raw file-byte Data-Code. TwinSpect expects a hex encoded compact code body,
    so we extract and return the first ISCC-SUM unit (Data-Code) body bytes.
    """
    try:
        import iscc_lib
        from iscc_bio.api import biocode

        _patch_lazy_bioformats_planes()
        results = biocode(fp, bits=64, source_type="auto")
        if not results:
            log.error(f"No biocode result for {fp}")
            return None

        if len(results) > 1:
            log.warning(f"{fp} produced {len(results)} scenes; using scene 0 only")

        data_code = results[0]["units"][0]
        _, _, _, _, body_bytes = iscc_lib.iscc_decode(data_code)
        log.success(f"{data_code} <- {Path(fp).name}")
        return body_bytes.hex()
    except Exception as e:
        log.error(f"Failed hashing {fp} - {e}")
        return None
