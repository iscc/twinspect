# -*- coding: utf-8 -*-
"""Bioimage format-conversion benchmark dataset.

The installer builds a reproducible clustered dataset from public Broad Bioimage
Benchmark Collection archives. Each selected source bioimage becomes one cluster:

    0000000/0original.TIF
    0000000/1variant_ome-tiff.ome.tiff
    0000000/2variant_tiff.tiff
    0000000/3variant_png.png

The converted cluster members are intended for benchmarking IMAGEWALK-based
bioimage Data-Code matching across storage formats. BioImage Convert (``imgcnv``)
is used for conversions because it supports microscopy formats beyond ordinary
Pillow/OpenCV image files.
"""

from __future__ import annotations

import csv
import json
import os
import random
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import ZipInfo

from loguru import logger as log
from remotezip import RemoteZip
from rich.progress import track

from twinspect import check_dir_fast, console

ONE_GIB = 1024**3
DEFAULT_CONVERT_TIMEOUT = 300
MANIFEST_PATH = Path(__file__).parent / "manifests" / "bioimage_convert_1000.csv"
BUILD_INFO_FILENAME = "_bioimage_convert_build.json"

# Public Broad Bioimage Benchmark Collection archives. These are deliberately
# normal ZIP archives with stable URLs and range-request support, so RemoteZip can
# extract selected files without downloading full multi-hundred-MB/GB archives.
BBBC_SOURCES = (
    {
        "label": "bbbc005",
        "url": "https://data.broadinstitute.org/bbbc/BBBC005/BBBC005_v1_images.zip",
        "info": "BBBC005 synthetic fluorescent cell images (Broad Bioimage Benchmark Collection)",
    },
    {
        "label": "bbbc006_z00",
        "url": "https://data.broadinstitute.org/bbbc/BBBC006/BBBC006_v1_images_z_00.zip",
        "info": "BBBC006 MCF7 z-stack microscopy images, z=00 (Broad Bioimage Benchmark Collection)",
    },
    {
        "label": "bbbc013_bmp",
        "url": "https://data.broadinstitute.org/bbbc/BBBC013/BBBC013_v1_images_bmp.zip",
        "info": "BBBC013 human U2OS cells in BMP format (Broad Bioimage Benchmark Collection)",
    },
)

# Conservative, broadly readable single-file output formats. Directory formats
# such as OME-NGFF/Zarr are intentionally excluded because TwinSpect currently
# treats benchmark assets as files.
CONVERSIONS = (
    ("ome-tiff", ".ome.tiff", "ome-tiff"),
    ("tiff", ".tiff", "tiff"),
    ("png", ".png", "png"),
)

IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@dataclass(frozen=True)
class BioimageSample:
    """A selected remote ZIP member."""

    source_label: str
    archive_url: str
    member_name: str
    file_size: int

    @property
    def suffix(self) -> str:
        suffixes = Path(self.member_name).suffixes
        return "".join(suffixes) if suffixes else Path(self.member_name).suffix


def install(dataset):
    # type: (object) -> Path
    """Install the BioImage Convert 1000-cluster benchmark dataset."""
    data_folder = dataset.data_folder
    if data_folder.exists():
        if dataset.checksum:
            check_dir_fast(data_folder, expected=dataset.checksum)
        log.debug(f"Using cached dataset {dataset.name}")
        return data_folder

    samples = int(dataset.samples or dataset.clusters or 1000)
    seed = int(dataset.seed or 0)
    selected = load_manifest(MANIFEST_PATH, samples=samples) or select_samples(
        samples=samples, seed=seed
    )

    tmp_root = Path(tempfile.mkdtemp(prefix=f"{dataset.label}-", dir=data_folder.parent))
    try:
        build_dataset(selected, tmp_root)
        write_build_info(tmp_root, selected)
        validate_dataset(tmp_root, expected_clusters=samples)
        tmp_root.replace(data_folder)
    except Exception:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise

    return data_folder


def load_manifest(manifest_path, samples=None):
    # type: (Path, int | None) -> list[BioimageSample]
    """Load a committed source manifest if available."""
    if not manifest_path.exists():
        return []

    rows = []
    with manifest_path.open("rt", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        expected = ["source_label", "archive_url", "member_name", "file_size"]
        if reader.fieldnames != expected:
            raise RuntimeError(f"Invalid manifest header in {manifest_path}: {reader.fieldnames!r}")
        for row in reader:
            rows.append(
                BioimageSample(
                    source_label=row["source_label"],
                    archive_url=row["archive_url"],
                    member_name=row["member_name"],
                    file_size=int(row["file_size"]),
                )
            )

    if samples is not None:
        if len(rows) < samples:
            raise RuntimeError(f"Manifest has {len(rows)} samples; need {samples}")
        rows = rows[:samples]
    return rows


def write_manifest(samples, manifest_path):
    # type: (list[BioimageSample], Path) -> Path
    """Write selected source samples as a reproducibility manifest."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("wt", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(
            outfile, fieldnames=["source_label", "archive_url", "member_name", "file_size"]
        )
        writer.writeheader()
        for sample in samples:
            writer.writerow(asdict(sample))
    return manifest_path


def select_samples(samples=1000, seed=0, max_file_size=ONE_GIB, sources=BBBC_SOURCES):
    # type: (int, int, int, tuple[dict, ...]) -> list[BioimageSample]
    """Select a reproducible set of public bioimage files from configured archives."""
    candidates = []
    for source in sources:
        for info in archive_image_infos(source["url"], max_file_size=max_file_size):
            candidates.append(
                BioimageSample(
                    source_label=source["label"],
                    archive_url=source["url"],
                    member_name=info.filename,
                    file_size=info.file_size,
                )
            )

    candidates = sorted(candidates, key=lambda item: (item.source_label, item.member_name))
    if len(candidates) < samples:
        raise RuntimeError(f"Only {len(candidates)} candidate bioimages available; need {samples}")

    rng = random.Random(seed)
    selected = rng.sample(candidates, samples)
    return sorted(selected, key=lambda item: (item.source_label, item.member_name))


def archive_image_infos(archive_url: str, max_file_size: int = ONE_GIB) -> list[ZipInfo]:
    """Return eligible image members from a remote ZIP archive."""
    with RemoteZip(archive_url) as zip_file:
        infos = [info for info in zip_file.infolist() if is_eligible_member(info, max_file_size)]
    return infos


def is_eligible_member(info: ZipInfo, max_file_size: int = ONE_GIB) -> bool:
    """Check whether a ZIP member is a usable bioimage candidate."""
    if info.is_dir() or info.file_size <= 0 or info.file_size > max_file_size:
        return False
    return Path(info.filename).suffix.lower() in IMAGE_EXTENSIONS


def build_dataset(samples, data_folder):
    # type: (list[BioimageSample], Path) -> None
    """Download selected originals and build conversion clusters."""
    data_folder.mkdir(parents=True, exist_ok=True)
    for cluster_id, sample in enumerate(
        track(samples, description="Building bioimage clusters", console=console)
    ):
        cluster_path = data_folder / f"{cluster_id:07d}"
        build_cluster(sample, cluster_path)
        validate_cluster(cluster_path)


def build_cluster(sample, cluster_path):
    # type: (BioimageSample, Path) -> None
    """Build one same-image/different-format cluster."""
    cluster_path.mkdir(parents=True, exist_ok=True)
    original_path = cluster_path / f"0original{sample.suffix}"
    extract_member(sample, original_path)
    validate_file_size(original_path)
    for idx, (label, suffix, format_name) in enumerate(CONVERSIONS, start=1):
        output_path = cluster_path / f"{idx}variant_{label}{suffix}"
        convert_file(original_path, output_path, format_name)
        validate_file_size(output_path)


def extract_member(sample, output_path):
    # type: (BioimageSample, Path) -> Path
    """Extract a single member from a remote ZIP archive to ``output_path``."""
    with tempfile.TemporaryDirectory(prefix="twinspect-bioimage-") as tmp_dir:
        tmp_dir = Path(tmp_dir)
        with RemoteZip(sample.archive_url) as zip_file:
            extracted = Path(zip_file.extract(sample.member_name, tmp_dir))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(extracted, output_path)
    validate_file_size(output_path)
    return output_path


def convert_file(input_path, output_path, format_name):
    # type: (Path, Path, str) -> Path
    """Convert ``input_path`` with BioImage Convert.

    The default command follows the documented BioImage Convertor/imgcnv style:
    ``imgcnv -i INPUT -o OUTPUT -t FORMAT``. For local installations with a
    different wrapper, set ``TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE`` to a shell-free
    argument template, e.g. ``"bioimageconvert --input {input} --output {output} --format {format}"``.
    """
    if output_path.exists() and output_path.stat().st_size > 0:
        validate_file_size(output_path)
        return output_path

    command = bioimage_convert_command(input_path, output_path, format_name)
    timeout = int(os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_TIMEOUT", DEFAULT_CONVERT_TIMEOUT))
    log.debug("Running BioImage Convert: {}", " ".join(command))
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "BioImage Convert executable not found. Install BioImage Convert and ensure "
            "`imgcnv` is on PATH, set TWINSPECT_BIOIMAGE_CONVERT_BIN, or set "
            "TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"BioImage Convert timed out after {timeout}s for "
            f"{input_path.name} -> {output_path.name}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"BioImage Convert failed for {input_path.name} -> {output_path.name}: "
            f"stdout={exc.stdout!r} stderr={exc.stderr!r}"
        ) from exc

    validate_file_size(output_path)
    return output_path


def bioimage_convert_command(input_path, output_path, format_name):
    # type: (Path, Path, str) -> list[str]
    """Build the BioImage Convert command line."""
    template = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE")
    if template:
        return [
            part.format(input=input_path, output=output_path, format=format_name)
            for part in shlex.split(template)
        ]
    binary = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_BIN") or "imgcnv"
    return [binary, "-i", str(input_path), "-o", str(output_path), "-t", format_name]


def bioimage_convert_version():
    # type: () -> str
    """Best-effort BioImage Convert version string for build metadata."""
    binary = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_BIN") or "imgcnv"
    for flag in ("--version", "-v"):
        try:
            result = subprocess.run(
                [binary, flag], check=False, capture_output=True, text=True, timeout=10
            )
        except Exception:
            continue
        text = (result.stdout or result.stderr or "").strip()
        if text:
            return text.splitlines()[0]
    return "unknown"


def validate_file_size(path, max_file_size=ONE_GIB):
    # type: (Path, int) -> None
    """Ensure a benchmark file is non-empty and within the configured hard size cap."""
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Missing expected bioimage file: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise RuntimeError(f"Empty bioimage file: {path}")
    if size > max_file_size:
        raise RuntimeError(f"Bioimage file exceeds {max_file_size} bytes: {path} ({size} bytes)")


def validate_cluster(cluster_path):
    # type: (Path) -> None
    """Validate expected original + conversion files for one cluster."""
    originals = sorted(cluster_path.glob("0original*"))
    if len(originals) != 1:
        raise RuntimeError(
            f"Expected exactly one original in {cluster_path}, found {len(originals)}"
        )
    validate_file_size(originals[0])

    for idx, (label, suffix, _) in enumerate(CONVERSIONS, start=1):
        path = cluster_path / f"{idx}variant_{label}{suffix}"
        validate_file_size(path)


def validate_dataset(data_folder, expected_clusters):
    # type: (Path, int) -> None
    """Validate cluster count and per-cluster completeness."""
    clusters = sorted(path for path in data_folder.iterdir() if path.is_dir())
    if len(clusters) != expected_clusters:
        raise RuntimeError(
            f"Expected {expected_clusters} clusters in {data_folder}, found {len(clusters)}"
        )
    for cluster in clusters:
        validate_cluster(cluster)


def write_build_info(data_folder, samples):
    # type: (Path, list[BioimageSample]) -> Path
    """Write reproducibility metadata into the installed dataset folder."""
    metadata = {
        "dataset": "bioimage_convert_1000",
        "sources": BBBC_SOURCES,
        "conversions": CONVERSIONS,
        "max_file_size": ONE_GIB,
        "bioimage_convert_command": bioimage_convert_command(
            Path("INPUT"), Path("OUTPUT"), "FORMAT"
        ),
        "bioimage_convert_version": bioimage_convert_version(),
        "samples": [asdict(sample) for sample in samples],
    }
    path = data_folder / BUILD_INFO_FILENAME
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return path
