"""Results Page Rendering"""

import json
import pathlib
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from loguru import logger as log
from PIL import Image
import pillow_avif  # noqa: F401 - registers AVIF format with Pillow

from twinspect.metrics.utils import best_threshold
from twinspect.options import opts
from twinspect.render.plot import plot_distribution, plot_effectiveness

HERE = pathlib.Path(__file__).parent.absolute()
TPL_PATH = HERE / "templates"
TPL_HEADER_PATH = HERE / "templates/results-header.md"
TPL_RESULT_PATH = TPL_HEADER_PATH / "templates/result.md"
OUT_PATH = HERE.parent.parent / "docs/results.md"
IMAGES_PATH = HERE.parent.parent / "docs/images"


def get_header():
    with open(TPL_HEADER_PATH, "rt", encoding="utf-8") as infile:
        return infile.read()


def render_header(data):
    env = Environment(loader=FileSystemLoader(TPL_PATH))
    template = env.get_template("results-header.md")
    rendered = template.render(data=data)
    return rendered


def get_metrics_files():
    return [mf for mf in opts.root_folder.glob("*metrics.json")]


def render_result(data):
    env = Environment(loader=FileSystemLoader(TPL_PATH))
    template = env.get_template("result.md")
    rendered = template.render(data=data)
    return rendered


def render_plot(plt, filename: str) -> str:
    """Render matplotlib plot to AVIF file and return relative path."""
    IMAGES_PATH.mkdir(parents=True, exist_ok=True)
    filepath = IMAGES_PATH / f"{filename}.avif"

    # Save to buffer as PNG, then convert to AVIF for smaller file size
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    plt.close()
    buf.seek(0)

    # Convert to AVIF using Pillow
    img = Image.open(buf)
    img.save(filepath, format="AVIF", quality=80)
    buf.close()

    return f"images/{filename}.avif"


def build_results_page():
    # type: () -> str
    """Render and save the `Datasets` page."""
    # markdown: str = get_header()
    markdown: str = ""
    overview = []

    for metrics_path in get_metrics_files():
        log.debug(f"Building results for {metrics_path.name}")
        with metrics_path.open() as infile:
            data = json.load(infile)
            algo_slug = data["algorithm"].replace("_", "-")
            ds_slug = "-".join(data["dataset"].split("_")[:3])
            data["algorithm"] = "-".join(
                frag.upper() for frag in data["algorithm"].split("_")
            ).replace("V0-", "")
            data["dataset"] = "-".join(frag.upper() for frag in data["dataset"].split("_")[:3])
            data["plot_dist"] = render_plot(
                plot_distribution(metrics_path), f"{algo_slug}-{ds_slug}-dist"
            )
            data["plot_eff"] = render_plot(
                plot_effectiveness(metrics_path), f"{algo_slug}-{ds_slug}-eff"
            )
            best = best_threshold(data)
            best["algorithm"] = data["algorithm"]
            best["dataset"] = data["dataset"]
            overview.append(best)
            markdown += render_result(data)

    markdown = render_header(overview) + markdown

    with OUT_PATH.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)
    return markdown
