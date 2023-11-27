"""
TED 2020 v1

See: https://opus.nlpl.eu/TED2020.php
"""
import io
from loguru import logger as log
from twinspect import check_dir_fast, check_dir_secure
from twinspect.datasets.download import download_multi
from twinspect.models import Dataset
from twinspect.options import opts
from pathlib import Path
import zipfile
from lxml import etree

DATA_HASH = "cedbbae5ae0f5ef3a92736a7754efa996af19a7924f253929649c4f8795a6982"


def download_ted_data() -> Path:
    download_folder = opts.root_folder / "ted_temp"
    if download_folder.exists():
        check_dir_secure(download_folder, expected=DATA_HASH)
        return download_folder

    urls = [URL_TPL.format(lng) for lng in LABSE_LANGUAGES]
    download_folder.mkdir(parents=True, exist_ok=True)
    download_multi(urls, download_folder)
    return download_folder


def clusterize(src: Path, dst: Path) -> Path:
    """
    Clusterize TED data.

    Extracts and converts .xml files to plain text from per language zipfiles into cluster folders.
    """
    for file in src.glob("*.zip"):
        log.debug(f"Clusterize {file}")
        lng = file.stem
        with zipfile.ZipFile(file) as zfile:
            for name in zfile.namelist():
                if not name.endswith(".xml"):
                    continue
                file_id = Path(name).stem.replace("ted2020-", "").replace(".xml", "").zfill(6)
                with zfile.open(name) as xml_file:
                    xml_content = xml_file.read()
                tree = etree.parse(io.BytesIO(xml_content))
                content = "".join(tree.xpath("//text()"))
                out_dir = dst / file_id
                out_dir.mkdir(parents=True, exist_ok=True)
                # Prefix en files with `!`
                fname = f"!{file_id}_{lng}.txt" if lng == "en" else f"{file_id}_{lng}.txt"
                out_file = out_dir / fname
                with out_file.open("wt", encoding="utf-8", newline="\n") as outf:
                    outf.write(content)
    check_dir_fast(dst)
    return dst


def install(dataset):
    # type: (Dataset) -> Path
    """Install TED Dataset"""

    # Check for existing data_folder
    if dataset.data_folder.exists():
        if dataset.checksum:
            check_dir_fast(dataset.data_folder, expected=dataset.checksum)
        log.debug(f"Using cached dataset {dataset.name}")
        return dataset.data_folder

    download_folder = download_ted_data()
    clusterize(download_folder, dataset.data_folder)
    return dataset.data_folder


URL_TPL = "https://opus.nlpl.eu/download.php?f=TED2020/v1/raw/{}.zip"

# Languages suppored by LaBSE minus unsupported TED languages
LABSE_LANGUAGES = [
    "af",
    "am",
    "ar",
    "as",
    "az",
    "be",
    "bg",
    "bn",
    "bo",
    "bs",
    "ca",
    "ceb",
    # "co",
    "cs",
    # "cy",
    "da",
    "de",
    "el",
    "en",
    "eo",
    "es",
    "et",
    "eu",
    "fa",
    "fi",
    "fr",
    # "fy",
    "ga",
    # "gd",
    "gl",
    "gu",
    "ha",
    # "haw",
    "he",
    "hi",
    # "hmn",
    "hr",
    "ht",
    "hu",
    "hy",
    "id",
    "ig",
    "is",
    "it",
    "ja",
    # "jv",
    "ka",
    "kk",
    "km",
    "kn",
    "ko",
    "ku",
    "ky",
    "la",
    "lb",
    "lo",
    "lt",
    "lv",
    "mg",
    # "mi",
    "mk",
    "ml",
    "mn",
    "mr",
    "ms",
    "mt",
    "my",
    "ne",
    "nl",
    # "no",
    # "ny",
    # "or",
    "pa",
    "pl",
    "pt",
    "ro",
    "ru",
    # "rw",
    "si",
    "sk",
    "sl",
    # "sm",
    # "sn",
    "so",
    "sq",
    "sr",
    # "st",
    # "su",
    "sv",
    "sw",
    "ta",
    "te",
    "tg",
    "th",
    "tk",
    "tl",
    "tr",
    "tt",
    "ug",
    "uk",
    "ur",
    "uz",
    "vi",
    # "wo",
    # "xh",
    # "yi",
    # "yo",
    "zh",
    # "zu",
]
