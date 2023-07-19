from jinja2 import Environment, FileSystemLoader
import os
import pathlib


HERE = pathlib.Path(__file__).parent.absolute()


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
