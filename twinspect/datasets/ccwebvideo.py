"""
CC Web Video

Metadata:

'7967': {
    'ID': '7967',
    'TopicID': '15',
    'Source': 'YouTube',
    'VideoName': '15_1335_Y.flv',
    'Duration': '02:50',
    'Format': 'flv',
    'Title': 'White&amp;Nerdy',
    'Duplicate': '0',
    'Url': 'http://www.youtube.com/watch?v=WyDqLI7dzMc',
    'Category': 'Music',
    'Tags': 'music funny song stupid',
    'Description': 'Music video:Weird Al-White & Nerdy',
    'Author': 'frunky5430',
    'vurl': 'http://vireo.cs.cityu.edu.hk/webvideo/videos/15/15_1335_Y.flv'
},


"""
import os
import zipfile
import re
import httpx
from loguru import logger as log
from pathlib import Path
from twinspect.datasets.integrity import check_dir_fast, hash_file_secure
from twinspect.options import opts
from twinspect.models import Dataset
from twinspect.datasets.download import download_file
import csv
from rich import print

DOWNLOAD_URL = "http://vireo.cs.cityu.edu.hk/webvideo/Info/Video_Complete.txt"
# DATA_FILE_PATH = os.path.join(DATA_PATH, "video_complete.txt")
DOWNLOAD_TPL = "http://vireo.cs.cityu.edu.hk/webvideo/videos/{QueryID}/{VideoName}"


def install(dataset):
    # type: (Dataset) -> Path
    """Install CC Web Video Dataset"""
    # Check for existing data_folder
    # if dataset.data_folder.exists():
    #     if dataset.checksum:
    #         check_dir_fast(dataset.data_folder, expected=dataset.checksum)
    #     log.debug(f"Using cached dataset {dataset.name}")
    #     return dataset.data_folder

    log.debug(f"Installing dataset {dataset.name}")
    dataset.data_folder.mkdir(exist_ok=True)
    meta = get_meta()
    seed_urls = get_seed_urls()
    ground_truth = get_ground_truth()
    hashes = set()
    etags = set()
    for seed_id in get_seeds():
        log.debug(f"Collecting CC WEB Video Seed {seed_id}")
        cluster_path = dataset.data_folder / f"cluster_{int(seed_id):02}"
        # Download Seed Video
        cluster_path.mkdir(exist_ok=True)
        url = seed_urls[seed_id]
        fp = download_file(url, cluster_path, overwrite=False)
        hashes.add(hash_file_secure(fp))
        for source_id, target_id, relation in ground_truth:
            if int(seed_id) < 19:
                continue
            if int(source_id) == int(seed_id) and relation == "S":
                url = meta[str(target_id)]["vurl"]
                local_file_path = cluster_path / url.split("/")[-1]
                if local_file_path.exists():
                    log.debug(f"Skip existing {local_file_path.name}")
                    hashes.add(hash_file_secure(local_file_path))
                    continue
                etag = httpx.head(url).headers.get("ETag")
                if etag in etags:
                    log.debug(f"Skip identical etag  {etag}")
                    continue
                try:
                    fp = download_file(url, cluster_path, overwrite=False)
                except Exception:
                    log.error(f"Failed download {url}")
                    continue
                etags.add(etag)
                try:
                    h = hash_file_secure(fp)
                except Exception:
                    continue
                if h in hashes:
                    os.remove(fp)
                hashes.add(h)

    # download_folder = opts.root_folder / f"fma_temp_{dataset.samples}_{dataset.seed}"
    # meta = get_meta(download_folder)
    # for source_id, target_id, relation in get_ground_truth():
    #
    # return meta


def get_meta():
    """Download and return parsed metadata"""

    data_file_path = opts.root_folder / "Video_Complete.txt"
    if not data_file_path.exists():
        log.info(f"Downloading web_video data: {data_file_path.name}")
        download_file(DOWNLOAD_URL, opts.root_folder)

    with data_file_path.open(mode="r", encoding="latin") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        data = {d["ID"]: d for d in reader}

    for id_, entry in data.items():
        entry["vurl"] = DOWNLOAD_TPL.format(QueryID=entry["TopicID"], VideoName=entry["VideoName"])

    return data


def get_ground_truth():
    """Download and parse ground truth data.

    A list of triplets with:
        qid: QueryID
        vid: VideoID
        status: Relation code from qid to vid.

    Status codes:
        E  - Exactly duplicate
        S  - Similar video
        V  - Different version
        M  - Major change
        L  - Long version
        X  - Dissimilar video
        -1 - Video does not exist

    returns: [(qid, vid, status)]
    """
    remote = "http://vireo.cs.cityu.edu.hk/webvideo/Info/Ground.zip"
    local_path = opts.root_folder / "Ground.zip"
    if not local_path.exists():
        download_file(remote, opts.root_folder)
    gt = []
    with zipfile.ZipFile(local_path) as gt_zip:
        for path in gt_zip.namelist():
            if path.startswith("GT/GT") and path.endswith(".rst"):
                query_id = re.findall(r"\d+", path)[0]
                data = gt_zip.open(path).read()
                for line in data.strip().splitlines():
                    v = line.split()
                    video_id, status = v[0], v[1]
                    gt.append((int(query_id), int(video_id), status.decode()))
    return gt


def get_seeds():
    """Download, parse and return IDs of seed videos."""
    resp = httpx.get("http://vireo.cs.cityu.edu.hk/webvideo/Info/Seed.txt")
    seeds = {}
    for line in resp.text.splitlines():
        seed_id, video_id = line.split()
        seed_id = seed_id.strip("*")
        seeds[seed_id] = video_id
    return seeds


def get_seed_urls():
    meta = get_meta()
    sv = {}
    for seed_id, video_id in get_seeds().items():
        url = meta[video_id]["vurl"]
        sv[seed_id] = url
    return sv


def seed_videos() -> list[str]:
    """Iter - download if neccessary - seed videos"""
    videos = []
    for sid, url in get_seed_urls().items():
        fpath = join(DATA_PATH, basename(url))
        if not exists(fpath):
            download(url, fpath)
        videos.append(fpath)
    return videos


if __name__ == "__main__":
    opts.root_folder = Path(r"e:/twinspect")
    ds = Dataset(
        name="CC Web Video",
        label="cc_web_video",
        url="http://vireo.cs.cityu.edu.hk/webvideo/Info/Video_Complete.txt",
        mode="video",
        installer="twinspect.datastes.ccwebvideo:install",
        samples=100,
        clusters=10,
        seed=0,
    )
    install(ds)
    # meta = install(ds)
    # print(meta)
