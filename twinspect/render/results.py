"""Results Page Rendering"""
import base64
import json
import pathlib
from io import BytesIO
from loguru import logger as log
from twinspect.render.plot import plot_distribution, plot_effectiveness
from twinspect.options import opts
from twinspect.metrics.utils import best_threshold
from jinja2 import Environment, FileSystemLoader

HERE = pathlib.Path(__file__).parent.absolute()
TPL_PATH = HERE / "templates"
TPL_HEADER_PATH = HERE / "templates/results-header.md"
TPL_RESULT_PATH = TPL_HEADER_PATH / "templates/result.md"
OUT_PATH = HERE.parent.parent / "docs/results.md"


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


def render_plot(plt) -> str:
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    img_data = buf.getvalue()
    buf.close()
    encoded_plot = base64.b64encode(img_data).decode()
    data_url = "data:image/png;base64," + encoded_plot
    return data_url


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
            data["algorithm"] = "-".join(
                frag.upper() for frag in data["algorithm"].split("_")
            ).replace("V0-", "")
            data["dataset"] = "-".join(frag.upper() for frag in data["dataset"].split("_")[:3])
            data["plot_dist"] = render_plot(plot_distribution(metrics_path))
            data["plot_eff"] = render_plot(plot_effectiveness(metrics_path))
            best = best_threshold(data)
            best["algorithm"] = data["algorithm"]
            best["dataset"] = data["dataset"]
            overview.append(best)
            markdown += render_result(data)

    markdown = render_header(overview) + markdown

    with OUT_PATH.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)
    return markdown
