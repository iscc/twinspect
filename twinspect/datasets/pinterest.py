"""
Pinterest Gold Standard Dataset

Paper: Evolution of a Web-Scale Near Duplicate Image Detection System

The paper presents a web-scale near-duplicate image detection system deployed at Pinterest together
 with a `gold standard` human-labeled dataset of ~53,000 pairs of near-diplocate images.
The dataset was created by using a crowdsourcing platform (86% non-near-dupe and 14% near-dupe
image pairs) and evaluated by human judges who have achieved high accuracy against a smaller
golden set. For each pair, 5 different human judges were asked whether the pair constitutes
near-dupe images.

https://www.pinterest.com/pin/100275529191933620
https://raw.githubusercontent.com/andreydg/www-neardup-paper/master/unified_paper_dataset.csv

CSV Ground Truth data is:
    img_url_a,img_url_b,0.0
    img_url_a,img_url_b,1.0

Where 0.0 is non-near-dupe and 0.1 is a near-dupe.

Stats:
    - 93702 total unique image urls
    - 81599 unique image urls that do NOT have 1 or more near-duplicates
    - 12867 unique image urls that one or more near-duplicates
    - 45847 pairs of image urls that are considered non-near-duplicates
    - 7422  pairs of image urls that are considered near-duplicates

Clustering Strategy:
    - given a target of x samples
    - we first cluster near-dupes using a graph (connected components)
    - For each clusterd file we download equivalent number of distractors
    - We stop when a total of x files has been collected.
"""
import csv
from pathlib import Path

import httpx
from loguru import logger as log
import httpx_cache as hc
from io import StringIO
from twinspect.datasets.ultils import Graph
from twinspect.models import Dataset
from twinspect.datasets.download import download_file
from rich.progress import track, Progress
from twinspect.globals import console
from twinspect.datasets.integrity import check_dir_fast


def install(dataset):
    # type: (Dataset) -> Path
    """
    Idempotent installation of a Pinterest subdataset.

    :param dataset: The dataset object to install.
    :return: The path to the dataset's data folder.
    """
    if dataset.data_folder.exists():
        if dataset.checksum:
            check_dir_fast(dataset.data_folder, expected=dataset.checksum)
        return dataset.data_folder

    # Create dataset folder
    dataset.data_folder.mkdir(exist_ok=True)

    # Download ground truth csv
    log.debug(f"Download {dataset.name} ground truth")
    with hc.Client(cache=hc.FileCache(), always_cache=True) as client:
        response = client.get(dataset.url)

    # Load CSV
    log.debug(f"Loading {dataset.name} ground truth")
    csv_file = StringIO(response.text)
    csv_reader = csv.reader(csv_file)
    data = [row for row in csv_reader]

    # Filter unique distractor image urls
    log.debug(f"Filter {dataset.name} distractor image urls")
    distractors = set()
    for a, b, _ in data:
        if a not in distractors:
            distractors.add(a)
        if b not in distractors:
            distractors.add(b)
    distractors = sorted(list(distractors))

    # Cluster near-dupe pairs
    log.debug(f"Cluster {dataset.name} near-dupe image urls")
    graph = Graph()
    for row in track(data, description="Build Graph", console=console):
        urla, urlb, is_near_dupe = row
        if is_near_dupe == "1.0":
            graph.add_edge(urla, urlb)

    # Download files into cluster folder structure
    log.debug(f"Download {dataset.name} images into cluster folders")
    cluster_count = 0
    samples_count = 0
    distract_count = 0
    client = httpx.Client()

    with Progress(console=console) as prog:
        task = prog.add_task("[cyan]Download Images", total=dataset.samples, completed=0)

        for cluster in graph.connected_components():
            if samples_count == dataset.samples:
                break
            cluster_count += 1
            cluster_folder = dataset.data_folder / f"cluster-{cluster_count:04}"
            cluster_folder.mkdir(exist_ok=True)
            # Download files for cluster
            for url in cluster:
                fp = download_file(url, target=cluster_folder, client=client)
                if fp:
                    samples_count += 1
                    log.debug(f"Retrieved {fp.relative_to(dataset.data_folder)}")
                    prog.update(task, advance=1)
                    if samples_count == dataset.samples:
                        break
            # Download equivalent number distractors
            for _ in range(len(cluster)):
                url = distractors[distract_count]
                fp = download_file(url, target=dataset.data_folder, client=client)
                if fp:
                    samples_count += 1
                    distract_count += 1
                    log.debug(f"Retrieved {fp.relative_to(dataset.data_folder)}")
                    prog.update(task, advance=1)
                    if samples_count == dataset.samples:
                        break
    if dataset.checksum:
        check_dir_fast(dataset.data_folder, expected=dataset.checksum)
    else:
        checksum = check_dir_fast(dataset.data_folder)
        log.warning(f"Take note of checksum for {dataset.name} -> {checksum}")
    return dataset.data_folder
