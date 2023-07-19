"""Datasets Page Rendering"""
import json
import pathlib
from twinspect.options import opts
from twinspect.datasets.info import dataset_info
from jinja2 import Environment, FileSystemLoader
from twinspect.models import DatasetInfo
from rich.filesize import decimal
import twinspect as ts

HERE = pathlib.Path(__file__).parent.absolute()
TPL_PATH = HERE / "templates"
TPL_HEADER_PATH = HERE / "templates/datasets-header.md"
TPL_DATASET_PATH = TPL_HEADER_PATH / "templates/dataset.md"
OUT_PATH = HERE.parent.parent / "docs/datasets.md"


def get_header():
    with open(TPL_HEADER_PATH, "rt", encoding="utf-8") as infile:
        return infile.read()


def get_data_folders():
    """Return data folder paths for which we have metrics."""
    data_folders = set()
    for metrics_path in opts.root_folder.glob("*metrics.json"):
        with metrics_path.open() as infile:
            data = json.load(infile)
        data_folders.add(opts.root_folder / data["dataset"])
    return data_folders


def augment_data(data: DatasetInfo) -> DatasetInfo:
    data.dataset_label = "-".join(data.dataset_label.split("_")).upper()
    data.total_size = decimal(data.total_size)
    return data


def render_dataset(data_folder):
    env = Environment(loader=FileSystemLoader(TPL_PATH))
    template = env.get_template("dataset.md")
    data = augment_data(dataset_info(data_folder))
    data = {k: v for k, v in sorted(data.dict().items())}

    # Collection optional dataset info from config.yml if present
    ds_obj = ts.Dataset.from_label(data["dataset_label"])
    if ds_obj and ds_obj.info:
        data["dataset_info"] = ds_obj.info

    # Collect optional transformation metadata from config.yml if present
    if data.get("transformations"):
        enriched = []
        for lbl in data["transformations"]:
            obj = ts.Transformation.from_label(lbl)
            if obj:
                enriched.append(f"**{obj.label}**: {obj.info}")
            else:
                enriched.append(lbl)
        data["transformations"] = enriched
    rendered = template.render(data=data)
    return rendered


def build_dataset_page():
    # type: () -> str
    """Render and save the `Datasets` page."""
    header: str = get_header()
    content: str = ""
    for data_folder in get_data_folders():
        content += render_dataset(data_folder)
    markdown = header + content
    with OUT_PATH.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)
    return markdown
