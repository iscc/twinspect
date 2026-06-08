# -*- coding: utf-8 -*-
"""Bioimage format-conversion benchmark dataset.

The installer builds a reproducible clustered dataset from public Broad Bioimage
Benchmark Collection archives. Each selected source bioimage becomes one cluster:

    0000000/0original.TIF
    0000000/1variant_ome-tiff.ome.tiff
    0000000/2variant_tiff.tiff
    0000000/3variant_png.png
    0000000/4variant_jpeg.jpg
    0000000/5variant_tiff-jpeg.tiff
    0000000/6variant_ome-tiff-jpeg.ome.tiff

The converted cluster members are intended for benchmarking IMAGEWALK-based
bioimage Data-Code matching across storage formats and codec semantics.
Bio-Formats ``bfconvert`` from pinned OME bftools is used by default because it
is mature, cross-platform, actively maintained, and supports microscopy formats
beyond ordinary Pillow/OpenCV image files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import random
import shlex
import shutil
import stat
import subprocess
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from loguru import logger as log
from remotezip import RemoteZip
from rich.progress import track

from twinspect import check_dir_fast, console

ONE_GIB = 1024**3
DEFAULT_CONVERT_TIMEOUT = 300
BIOFORMATS_VERSION = "8.5.0"
BFTOOLS_URL = (
    f"https://downloads.openmicroscopy.org/bio-formats/{BIOFORMATS_VERSION}/artifacts/bftools.zip"
)
BFTOOLS_SHA256 = "07a3bb1d3de84da3a709655a1008cb2d9b19becc5bad4ae4112633aec9380478"
MAX_BFTOOLS_DOWNLOAD_BYTES = 128 * 1024 * 1024
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
# treats benchmark assets as files. The first three conversions form an identity
# tier on the BBBC smoke set; the JPEG-compressed conversions are real codec
# conversions that produce non-identical IMAGEWALK bitstreams without synthetic
# brightness/blur/crop/etc. manipulations.
CONVERSIONS = (
    ("ome-tiff", ".ome.tiff", "ome-tiff", ()),
    ("tiff", ".tiff", "tiff", ()),
    ("png", ".png", "png", ()),
    ("jpeg", ".jpg", "jpeg", ()),
    ("tiff-jpeg", ".tiff", "tiff", ("-compression", "JPEG", "-quality", "0.90")),
    (
        "ome-tiff-jpeg",
        ".ome.tiff",
        "ome-tiff",
        ("-compression", "JPEG", "-quality", "0.90"),
    ),
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
    for idx, (label, suffix, format_name, convert_args) in enumerate(CONVERSIONS, start=1):
        output_path = cluster_path / f"{idx}variant_{label}{suffix}"
        convert_file(original_path, output_path, format_name, convert_args)
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


def convert_file(input_path, output_path, format_name, convert_args=()):
    # type: (Path, Path, str, tuple[str, ...]) -> Path
    """Convert ``input_path`` with BioImage Convert.

    The default converter is the pinned Bio-Formats command-line tool
    (``bfconvert`` from ``bftools.zip``), which is actively maintained by OME,
    distributed as a Java application, and ships shell/batch launchers for
    Linux, macOS, and Windows. For local installations with a different wrapper,
    set ``TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE`` to a shell-free argument
    template, e.g. ``"bioimageconvert --input {input} --output {output} --format {format}"``.
    """
    if output_path.exists() and output_path.stat().st_size > 0:
        validate_file_size(output_path)
        return output_path

    command = bioimage_convert_command(input_path, output_path, format_name, convert_args)
    timeout = int(os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_TIMEOUT", DEFAULT_CONVERT_TIMEOUT))
    log.debug("Running BioImage Convert: {}", " ".join(command))
    try:
        env = os.environ.copy()
        env.setdefault("NO_UPDATE_CHECK", "1")
        subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=timeout, env=env
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Bioimage conversion executable not found. TwinSpect downloads pinned OME Bio-Formats "
            "bftools by default; custom TWINSPECT_BIOIMAGE_CONVERT_BIN values must point to an "
            "existing executable. Use TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE for non-imgcnv-style "
            "custom converters."
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


def bioimage_convert_command(input_path, output_path, format_name, convert_args=()):
    # type: (Path, Path, str, tuple[str, ...]) -> list[str]
    """Build the BioImage conversion command line."""
    template = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE")
    if template:
        options = " ".join(shlex.quote(option) for option in convert_args)
        return [
            part.format(input=input_path, output=output_path, format=format_name, options=options)
            for part in shlex.split(template)
        ]
    binary = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_BIN")
    if binary:
        if convert_args:
            raise RuntimeError(
                "TWINSPECT_BIOIMAGE_CONVERT_BIN uses the legacy imgcnv argument shape and cannot "
                "represent Bio-Formats codec options. Use TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE "
                "with an {options} placeholder for codec-specific conversions."
            )
        return [binary, "-i", str(input_path), "-o", str(output_path), "-t", format_name]
    bfconvert = ensure_bioformats_tools()
    return [str(bfconvert), *convert_args, str(input_path), str(output_path)]


def default_bioformats_cache_dir():
    # type: () -> Path
    """Return the default cache directory for pinned Bio-Formats tools."""
    override = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_CACHE")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "twinspect" / "bioformats"


def bioformats_bfconvert_name():
    # type: () -> str
    """Return the platform-specific Bio-Formats launcher name."""
    return "bfconvert.bat" if platform.system() == "Windows" else "bfconvert"


def ensure_bioformats_tools(cache_dir=None):
    # type: (Path | None) -> Path
    """Download, verify, and extract pinned Bio-Formats command-line tools.

    Bio-Formats bftools is a cross-platform Java distribution containing Unix
    shell launchers and Windows ``.bat`` launchers. We pin the exact archive URL
    and SHA-256 digest instead of relying on a moving ``latest`` endpoint.
    """
    cache_dir = Path(cache_dir) if cache_dir is not None else default_bioformats_cache_dir()
    target_dir = cache_dir / f"bftools-{BIOFORMATS_VERSION}"
    bfconvert = target_dir / bioformats_bfconvert_name()
    jar = target_dir / "bioformats_package.jar"
    if bfconvert.exists() and jar.exists():
        make_bioformats_scripts_executable(target_dir)
        return bfconvert

    cache_dir.mkdir(parents=True, exist_ok=True)
    archive_path = cache_dir / f"bftools-{BIOFORMATS_VERSION}.zip"
    download_file(BFTOOLS_URL, archive_path)
    verify_sha256(archive_path, BFTOOLS_SHA256)

    extract_root = cache_dir / f".extract-bftools-{BIOFORMATS_VERSION}"
    shutil.rmtree(extract_root, ignore_errors=True)
    extract_root.mkdir(parents=True)
    try:
        safe_extract_zip(archive_path, extract_root)
        extracted = extract_root / "bftools"
        if not (extracted / bioformats_bfconvert_name()).exists():
            raise RuntimeError(f"Bio-Formats archive did not contain {bioformats_bfconvert_name()}")
        shutil.rmtree(target_dir, ignore_errors=True)
        extracted.replace(target_dir)
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)

    make_bioformats_scripts_executable(target_dir)
    return bfconvert


def make_bioformats_scripts_executable(target_dir):
    # type: (Path) -> None
    """Mark Unix Bio-Formats launcher scripts executable."""
    if platform.system() == "Windows":
        return
    for script in target_dir.iterdir():
        if script.is_file() and script.suffix in {"", ".sh"}:
            script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def download_file(url, output_path, max_bytes=MAX_BFTOOLS_DOWNLOAD_BYTES):
    # type: (str, Path, int) -> Path
    """Download ``url`` to ``output_path`` without loading the whole body at once."""
    bytes_written = 0
    with urllib.request.urlopen(url, timeout=120) as response:
        with open(output_path, "wb") as out_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise RuntimeError(f"Download exceeded maximum size of {max_bytes} bytes")
                out_file.write(chunk)
    return output_path


def verify_sha256(path, expected):
    # type: (Path, str) -> None
    """Verify a file SHA-256 digest."""
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"Bio-Formats bftools checksum mismatch for {path}: expected {expected}, got {actual}"
        )


def safe_extract_zip(archive_path, target_dir):
    # type: (Path, Path) -> None
    """Extract a ZIP archive while rejecting path traversal entries."""
    target_dir = target_dir.resolve()
    with ZipFile(archive_path) as zip_file:
        for member in zip_file.infolist():
            destination = (target_dir / member.filename).resolve()
            if not destination.is_relative_to(target_dir):
                raise RuntimeError(f"Unsafe archive member path: {member.filename}")
        zip_file.extractall(target_dir)


def bioimage_convert_version():
    # type: () -> str
    """Best-effort BioImage converter version string for build metadata."""
    template = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_TEMPLATE")
    if template:
        return f"custom template: {template}"
    binary = os.environ.get("TWINSPECT_BIOIMAGE_CONVERT_BIN")
    if binary:
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
        return "custom binary: unknown"
    return f"Bio-Formats bftools {BIOFORMATS_VERSION}"


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

    for idx, (label, suffix, _, _) in enumerate(CONVERSIONS, start=1):
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
