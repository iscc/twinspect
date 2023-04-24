# -*- coding: utf-8 -*-
import shutil

import twinspect as ts
import importlib
import pathlib
import yaml

__all__ = [
    "load_function",
    "install_dataset",
    "clusterize",
]

ROOT = pathlib.Path(__file__).parent.parent.absolute()


def load_function(path: str):
    module_path, function_name = path.split(':')
    module = importlib.import_module(module_path)
    function = getattr(module, function_name)
    return function


def install_dataset(dataset: ts.Dataset) -> pathlib.Path:
    install = load_function(dataset.installer)
    return install(dataset)


def clusterize(src: pathlib.Path, dst: pathlib.Path, clusters: int):
    """Copy files from source to destination into a cluster folder structure."""
    clustered = 0
    for path in src.rglob("*"):
        if path.is_file():
            if clustered < clusters:
                cluster_folder_name = f"{clustered:07d}"
                target = dst / cluster_folder_name
                target.mkdir()
                shutil.copy(path, target)
                clustered += 1
            else:
                shutil.copy(path, dst)


def format_yml():
    """Format all .yml files"""
    for f in ROOT.glob("**/*.yml"):
        with open(f, "rt", encoding="utf-8") as infile:
            data = yaml.safe_load(infile)
        with open(f, "wt", encoding="utf-8", newline="\n") as outf:
            yaml.safe_dump(
                data,
                outf,
                indent=2,
                width=100,
                encoding="utf-8",
                sort_keys=False,
                default_flow_style=False,
                default_style=None,
                allow_unicode=True,
            )


def fix_line_endings():
    """Normalize all line endings to unix LF"""
    WINDOWS_LINE_ENDING = b"\r\n"
    UNIX_LINE_ENDING = b"\n"
    extensions = {".py", ".toml", ".lock", ".md", ".yml", ".yaml"}
    for fp in ROOT.glob("**/*"):
        if fp.suffix in extensions:
            with open(fp, "rb") as infile:
                content = infile.read()
            new_content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)
            if new_content != content:
                with open(fp, "wb") as outfile:
                    outfile.write(new_content)
                print(f"       fixed line endings for {fp.name}")
