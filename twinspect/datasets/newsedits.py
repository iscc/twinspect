"""NewsEdits Reuters dataset installer.

Downloads and processes the Reuters subset of the NewsEdits dataset for benchmarking
text-based content identification algorithms. The dataset contains news article revisions
from Reuters (2012-2020).

Source: https://github.com/isi-nlp/NewsEdits
Paper: https://arxiv.org/abs/2206.07106 (NAACL 2022)
License: Creative Commons Attribution 4.0
"""

import gzip
import html
import re
import shutil
import sqlite3
import unicodedata
from pathlib import Path

import blake3
import gdown
from loguru import logger as log
from rich.progress import Progress

import twinspect as ts
from twinspect.datasets.integrity import check_dir_fast
from twinspect.globals import console
from twinspect.models import Dataset
from twinspect.options import opts

REUTERS_FILE_ID = "12BEhXmqTqGIfiOfWl6Mx_CPU4BvDUX8x"


def install(dataset):
    # type: (Dataset) -> Path
    """Install NewsEdits Reuters dataset and return its data_folder."""
    # Check for existing data_folder with checksum verification
    if dataset.data_folder.exists():
        if dataset.checksum:
            check_dir_fast(dataset.data_folder, expected=dataset.checksum)
        log.debug(f"Using cached dataset {dataset.name}")
        return dataset.data_folder

    log.info(f"Installing dataset {dataset.name}")

    # Download Reuters database
    db_path = download_reuters_db()

    # Extract to cluster structure
    extract_clusters(
        db_path=db_path,
        output_dir=dataset.data_folder,
        max_clusters=dataset.clusters,
        min_versions=2,
        min_content_length=dataset.min_content_length or 0,
        max_length_variation=dataset.max_length_variation,
    )

    # Verify integrity
    if dataset.checksum:
        check_dir_fast(dataset.data_folder, expected=dataset.checksum)
    else:
        checksum = check_dir_fast(dataset.data_folder)
        log.warning(f"Take note of checksum for {dataset.name} -> {checksum}")

    return dataset.data_folder


def download_reuters_db():
    # type: () -> Path
    """Download and decompress Reuters database to root folder."""
    gz_path = opts.root_folder / "newsedits_reuters.db.gz"
    db_path = opts.root_folder / "newsedits_reuters.db"

    if db_path.exists() and db_path.stat().st_size > 0:
        log.debug(f"Using cached database at {db_path}")
        return db_path

    log.info("Downloading NewsEdits Reuters database (~221 MB compressed)...")
    gdown.download(id=REUTERS_FILE_ID, output=str(gz_path), quiet=False)

    log.info("Decompressing database...")
    with gzip.open(gz_path, "rb") as f_in:
        with open(db_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Clean up compressed file
    gz_path.unlink()
    log.info(f"Database ready at {db_path}")

    return db_path


def filter_by_length_variation(versions, max_variation):
    # type: (list[tuple[int, str]], float | None) -> list[tuple[int, str]]
    """Keep only versions within max_variation of each other.

    Uses a greedy approach: finds the largest group of versions where each version
    is within max_variation (as a fraction) of all other versions in the group.
    """
    if not versions or max_variation is None or max_variation <= 0:
        return versions

    # Sort by content length
    sorted_versions = sorted(versions, key=lambda v: len(v[1]))

    # Find largest group of versions within tolerance of each other
    best_group = []
    for i, (_, content_i) in enumerate(sorted_versions):
        len_i = len(content_i)
        group = [sorted_versions[i]]
        for j, (_, content_j) in enumerate(sorted_versions):
            if i == j:
                continue
            len_j = len(content_j)
            # Check if within tolerance of ALL versions in current group
            if all(abs(len_j - len(c)) / len(c) <= max_variation for _, c in group):
                group.append(sorted_versions[j])
        if len(group) > len(best_group):
            best_group = group

    return best_group


def extract_clusters(
    db_path, output_dir, max_clusters, min_versions, min_content_length=0, max_length_variation=None
):
    # type: (Path, Path, int, int, int, float | None) -> None
    """Extract article clusters from SQLite database.

    Creates a cluster folder structure where each cluster contains multiple versions
    of the same article as plaintext files. Articles shorter than min_content_length
    are excluded. If max_length_variation is set, only versions within that fraction
    of each other's length are kept. Iterates until max_clusters valid clusters are created.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Select all entries with at least min_versions versions, ordered deterministically
    cursor.execute(
        """
        SELECT entry_id, COUNT(*) as version_count
        FROM entryversion
        GROUP BY entry_id
        HAVING version_count >= ?
        ORDER BY entry_id
    """,
        (min_versions,),
    )

    entries = cursor.fetchall()
    log.info(f"Found {len(entries)} entries with >= {min_versions} versions")

    clusters_created = 0
    total_files = 0

    with Progress(console=console) as prog:
        task = prog.add_task(f"Extracting {output_dir.name}", total=max_clusters)

        for entry_id, _ in entries:
            if clusters_created >= max_clusters:
                break

            # Get all versions for this entry, ordered by version number
            cursor.execute(
                """
                SELECT version, title, summary
                FROM entryversion
                WHERE entry_id = ?
                ORDER BY version
            """,
                (entry_id,),
            )

            versions = cursor.fetchall()

            # Extract and deduplicate versions
            seen_hashes = set()
            unique_versions = []

            for version_num, title, summary in versions:
                content = html_to_plaintext(title or "", summary or "")
                if not content.strip():
                    continue
                if len(content) < min_content_length:
                    continue

                content_hash = blake3.blake3(content.encode("utf-8")).hexdigest()
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_versions.append((version_num, content))

            # Apply length variation filter
            unique_versions = filter_by_length_variation(unique_versions, max_length_variation)

            # Skip if fewer than min_versions unique versions
            if len(unique_versions) < min_versions:
                continue

            # Create cluster folder
            cluster_folder = output_dir / f"{clusters_created:07d}"
            cluster_folder.mkdir(parents=True, exist_ok=True)

            # Write version files (0v1.txt, 0v2.txt, etc.)
            for idx, (version_num, content) in enumerate(unique_versions, start=1):
                file_path = cluster_folder / f"0v{idx}.txt"
                file_path.write_text(content, encoding="utf-8", newline="\n")
                total_files += 1

            clusters_created += 1
            prog.update(task, advance=1)

    conn.close()
    log.info(f"Created {clusters_created} clusters with {total_files} total files")


def html_to_plaintext(title, html_content):
    # type: (str, str) -> str
    """Convert HTML article content to normalized plaintext."""
    # Decode HTML entities
    text = html.unescape(html_content)

    # Preserve paragraph structure
    text = re.sub(r"</p>\s*<p[^>]*>", "\n\n", text)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # NFKC Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Remove control characters (keep newlines)
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in "\n")

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Combine title + content
    title = title.strip()
    text = text.strip()

    if title and text:
        return f"{title}\n\n{text}"
    elif title:
        return title
    else:
        return text
