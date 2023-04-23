import twinspect as ts
import pathlib
from remotezip import RemoteZip
import random
from rich.progress import track


def install(dataset: ts.Dataset, path: pathlib.Path) -> pathlib.Path:
    audio_file_names = []
    data_folder = path / dataset.name
    if data_folder.exists():
        return data_folder

    with RemoteZip(dataset.url) as zip:
        # collect all names of audio files
        for file_name in zip.namelist():
            if file_name.endswith('.mp3'):
                audio_file_names.append(file_name)
        # Select samples
        random.seed(0)
        sample_file_names = random.sample(audio_file_names, dataset.samples)
        # Extract examples
        for sfn in track(sample_file_names, description="FMA Download"):
            zip.extract(sfn, data_folder)
