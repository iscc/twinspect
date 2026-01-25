"""Results Page Rendering - Multi-page structure by media type."""

import json
import pathlib
from collections import defaultdict
from io import BytesIO

from jinja2 import Environment, FileSystemLoader
from loguru import logger as log
from PIL import Image
import pillow_avif  # noqa: F401 - registers AVIF format with Pillow

from twinspect.metrics.utils import best_threshold
from twinspect.models import Dataset
from twinspect.options import cnf, opts
from twinspect.render.plot import plot_distribution, plot_effectiveness

HERE = pathlib.Path(__file__).parent.absolute()
TPL_PATH = HERE / "templates"
DOCS_PATH = HERE.parent.parent / "docs"
RESULTS_PATH = DOCS_PATH / "results"
IMAGES_PATH = DOCS_PATH / "images"

MODE_TITLES = {
    "text": "Text",
    "image": "Image",
    "audio": "Audio",
    "video": "Video",
}


def get_algorithm_order():
    """Get algorithm labels in order from config."""
    return [algo.label for algo in cnf.algorithms]


def get_metrics_files():
    """Get all metrics JSON files from the root folder."""
    return list(opts.root_folder.glob("*metrics.json"))


def render_template(template_name, data):
    """Render a Jinja2 template with the given data."""
    env = Environment(loader=FileSystemLoader(TPL_PATH))
    template = env.get_template(template_name)
    return template.render(data=data)


def render_plot(plt, filename):
    """Render matplotlib plot to AVIF file and return the filename."""
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

    return f"{filename}.avif"


def get_mode_for_dataset(dataset_label):
    """Get the mode for a dataset based on its label."""
    ds = Dataset.from_label(dataset_label)
    if ds:
        return ds.mode.value
    return None


def format_algorithm_name(algo_label):
    """Format algorithm label for display."""
    return "-".join(frag.upper() for frag in algo_label.split("_")).replace("V0-", "")


def format_dataset_name(ds_label):
    """Format dataset label for display."""
    return "-".join(frag.upper() for frag in ds_label.split("_")[:3])


def process_metrics_file(metrics_path):
    """Process a single metrics file and return structured data."""
    with metrics_path.open() as infile:
        data = json.load(infile)

    algo_slug = data["algorithm"].replace("_", "-")
    ds_slug = "-".join(data["dataset"].split("_")[:3])

    # Get mode from dataset
    mode = get_mode_for_dataset(data["dataset"])

    # Store original labels for sorting
    data["algorithm_label"] = data["algorithm"]
    data["dataset_label"] = data["dataset"]

    # Format names for display
    data["algorithm_display"] = format_algorithm_name(data["algorithm"])
    data["dataset_display"] = format_dataset_name(data["dataset"])
    data["mode"] = mode

    # Generate plots and store just the filename (not full path)
    dist_filename = render_plot(plot_distribution(metrics_path), f"{algo_slug}-{ds_slug}-dist")
    eff_filename = render_plot(plot_effectiveness(metrics_path), f"{algo_slug}-{ds_slug}-eff")

    data["plot_dist_filename"] = dist_filename
    data["plot_eff_filename"] = eff_filename

    # Calculate best threshold
    best = best_threshold(data)
    best["algorithm"] = data["algorithm_display"]
    best["dataset"] = data["dataset_display"]
    data["best"] = best

    return data


def render_result_for_page(data, image_prefix="images"):
    """Render a single result section with correct image paths."""
    # Create a copy with adjusted paths for the template
    template_data = {
        "algorithm": data["algorithm_display"],
        "dataset": data["dataset_display"],
        "plot_eff": f"{image_prefix}/{data['plot_eff_filename']}"
        if data.get("plot_eff_filename")
        else None,
        "plot_dist": f"{image_prefix}/{data['plot_dist_filename']}"
        if data.get("plot_dist_filename")
        else None,
        "metrics": data.get("metrics", {}),
    }
    return render_template("result.md", template_data)


def build_overview_page(all_results, modes_with_results):
    """Build the main overview page with navigation to media type pages."""
    overview_data = []
    modes_data = []

    # Collect overview data from all results
    for result in all_results:
        overview_data.append(result["best"])

    # Build mode navigation data
    for mode in ["text", "image", "audio", "video"]:
        mode_results = [r["best"] for r in all_results if r["mode"] == mode]
        modes_data.append(
            {
                "name": mode,
                "title": MODE_TITLES[mode],
                "results": mode_results,
            }
        )

    data = {
        "overview": overview_data,
        "modes": modes_data,
    }

    markdown = render_template("results-overview.md", data)

    out_path = DOCS_PATH / "results.md"
    with out_path.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)

    log.info(f"Built overview page: {out_path}")
    return markdown


def build_mode_page(mode, results):
    """Build a page for a specific media type."""
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)

    # Build overview for this mode
    overview_data = [r["best"] for r in results]

    # Mode-specific explanations
    explanations = {
        "text": "Text similarity algorithms identify near-duplicate documents that may have undergone format conversion, minor edits, or text extraction differences.",
        "image": "Image similarity algorithms detect visually similar images including crops, resizes, color adjustments, and format conversions.",
        "audio": "Audio similarity algorithms match audio content across different encodings, compressions, and minor modifications like trimming or fading.",
        "video": "Video similarity algorithms identify matching video content despite transcoding, resolution changes, or minor edits.",
    }

    header_data = {
        "title": MODE_TITLES[mode],
        "overview": overview_data,
        "explanation": explanations.get(mode, ""),
    }

    # Build page content
    markdown = render_template("results-mode-header.md", header_data)

    # Add individual results with correct relative image path
    for result in results:
        markdown += "\n---\n\n"
        markdown += render_result_for_page(result, image_prefix="../images")

    out_path = RESULTS_PATH / f"{mode}.md"
    with out_path.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)

    log.info(f"Built {mode} results page: {out_path}")
    return markdown


def build_placeholder_page(mode):
    """Build a placeholder page for a mode without results."""
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)

    markdown = f"""# {MODE_TITLES[mode]} Results

!!! warning "No Results Available"
    No benchmark results are available for {MODE_TITLES[mode].lower()} algorithms yet.

    Check back later or run the benchmark suite to generate results.
"""

    out_path = RESULTS_PATH / f"{mode}.md"
    with out_path.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)

    log.info(f"Built placeholder page for {mode}: {out_path}")


def build_results_page():
    """Build all results pages (overview + per-mode pages)."""
    metrics_files = get_metrics_files()

    all_results = []

    if metrics_files:
        # Process all metrics files
        for metrics_path in metrics_files:
            log.debug(f"Processing metrics: {metrics_path.name}")
            result = process_metrics_file(metrics_path)
            all_results.append(result)

    # Sort results by algorithm order from config
    algo_order = get_algorithm_order()

    def sort_key(result):
        """Sort by algorithm order in config, then by dataset label."""
        algo_label = result.get("algorithm_label", "")
        try:
            algo_idx = algo_order.index(algo_label)
        except ValueError:
            algo_idx = len(algo_order)  # Unknown algorithms go last
        return (algo_idx, result.get("dataset_label", ""))

    all_results.sort(key=sort_key)

    # Group results by mode (preserving sort order)
    results_by_mode = defaultdict(list)
    for result in all_results:
        if result["mode"]:
            results_by_mode[result["mode"]].append(result)

    # Build overview page
    build_overview_page(all_results, set(results_by_mode.keys()))

    # Build per-mode pages (all modes, even if no results)
    for mode in ["text", "image", "audio", "video"]:
        if mode in results_by_mode:
            build_mode_page(mode, results_by_mode[mode])
        else:
            build_placeholder_page(mode)

    return "Results pages built successfully"
