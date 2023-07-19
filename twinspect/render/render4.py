import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
import os


def render_template_and_save(data, template_path, output_path):
    # Get the directory and filename from the template path
    directory, filename = os.path.split(template_path)

    # Set up the Jinja2 environment
    env = Environment(loader=FileSystemLoader(directory))

    # Load the template
    template = env.get_template(filename)

    # Render the template with the data
    rendered_html = template.render(data=data)

    # Save the rendered HTML to the output path
    with open(output_path, "w") as file:
        file.write(rendered_html)


import pathlib
import sys


HERE = pathlib.Path(__file__).parent.absolute()

if __name__ == "__main__":
    met = Path(r"E:\twinspect\audio_code_v0_64-fma_5000-142e3bd331044320-metrics.json")
    tpl = HERE / "result.html"
    out = HERE / "out.html"
    with met.open("r") as json_file:
        data = json.load(json_file)
    render_template_and_save(data, tpl, out)
