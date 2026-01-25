"""Algorithms Page Rendering"""

import pathlib
from jinja2 import Environment, FileSystemLoader
import twinspect as ts

HERE = pathlib.Path(__file__).parent.absolute()
TPL_PATH = HERE / "templates"
TPL_HEADER_PATH = HERE / "templates/algorithms-header.md"
OUT_PATH = HERE.parent.parent / "docs/algorithms.md"


def get_header():
    """Return the header content for the algorithms page."""
    with open(TPL_HEADER_PATH, "rt", encoding="utf-8") as infile:
        return infile.read()


def render_algorithm(algo):
    """Render a single algorithm entry using the template."""
    env = Environment(loader=FileSystemLoader(TPL_PATH))
    template = env.get_template("algorithm.md")
    return template.render(data=algo)


def build_algorithms_page():
    """Render and save the Algorithms page."""
    header = get_header()
    content = ""
    for algo in ts.cnf.algorithms:
        content += render_algorithm(algo)
    markdown = header + content
    with OUT_PATH.open(mode="wt", encoding="utf-8", newline="\n") as outf:
        outf.write(markdown)
    return markdown
