# -*- coding: utf-8 -*-
"""ISCC-BIO algorithm implementations for TwinSpect benchmarking."""

from pathlib import Path
from typing import Optional

from loguru import logger as log


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
