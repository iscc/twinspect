import shutil
from concurrent.futures import ProcessPoolExecutor
import twinspect as ts
import pathlib
from remotezip import RemoteZip
import random
from rich.progress import track


def install(dataset: ts.Dataset) -> pathlib.Path:
    """Install FMA Dataset"""
    data_folder = clusterize(dataset)
    return data_folder


def process_transformation(tansform):
    ts_obj, target_file = tansform
    ts_func = ts.load_function(ts_obj.function)
    ts_func(target_file, *ts_obj.params)


def clusterize(dataset: ts.Dataset) -> pathlib.Path:
    """Create data folder with clustered transformations"""

    download_folder = download(dataset)
    data_folder = ts.opts.root_folder / dataset.label
    # Use cached data folder  if available
    if data_folder.exists():
        if dataset.data_hash:
            ts.check_folder(data_folder, dataset.data_hash)
        print(f"Using cached data folder {data_folder}")
        return data_folder

    # Process raw data to data folder
    clusters = dataset.clusters
    clustered = 0
    audio_files = [p for p in download_folder.rglob("*") if p.is_file()]
    for path in track(audio_files, description=f"Processing {dataset.name}"):
        if clustered < clusters:
            cluster_folder_name = f"{clustered:07d}"
            target_dir = data_folder / cluster_folder_name
            target_dir.mkdir(parents=True)
            target_file = target_dir / f"0{path.name}"
            shutil.copy(path, target_file)
            clustered += 1
            # Process transformations in parallel
            transforms = [(tf, target_file) for tf in ts.cnf.transformations if tf.mode == ts.Mode.audio]
            with ProcessPoolExecutor() as excecutor:
                excecutor.map(process_transformation, transforms)
        else:
            shutil.copy(path, data_folder)
    data_hash = ts.hash_folder(data_folder)
    print(f"data_hash: {data_hash} (add to configuration for integrity verfification)")
    return data_folder


def download(dataset: ts.Dataset) -> pathlib.Path:
    """Download FMA Dataset and return download folder"""
    # Use cached download folder if available
    download_folder = ts.opts.root_folder / f"downloads/{dataset.label}"
    if download_folder.exists():
        if dataset.download_hash:
            ts.check_folder(download_folder, dataset.download_hash)
        print(f"Using cached download folder {download_folder}")
        return download_folder

    # Collect, download and extract samples
    download_folder.mkdir(parents=True)
    audio_file_names = []
    with RemoteZip(dataset.url) as zipfile:
        # collect all names of audio files
        for file_name in zipfile.namelist():
            if file_name.endswith('.mp3'):
                audio_file_names.append(file_name)
        # Select samples
        random.seed(dataset.seed)
        sample_file_names = random.sample(audio_file_names, dataset.samples)
        # Extract examples
        for sfn in track(sample_file_names, description=f"Download {dataset.name}"):
            zipfile.extract(sfn, download_folder)
    download_hash = ts.hash_folder(download_folder)
    print(f"download_hash: {download_hash} (add to configuration for integrity verfification)")
    return download_folder
