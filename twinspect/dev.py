"""Development Tools"""
from pathlib import Path
import ruamel.yaml


ROOT = Path(__file__).parent.parent.absolute()


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


def format_yml():
    """Format all .yml files"""
    yaml = ruamel.yaml.YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 95
    yaml.allow_unicode = True
    yaml.default_flow_style = False
    yaml.default_style = None
    yaml.sort_keys = False

    for f in ROOT.glob("**/*.yml"):
        with open(f, "rt", encoding="utf-8") as infile:
            data = yaml.load(infile)
        with open(f, "wt", encoding="utf-8", newline="\n") as outf:
            yaml.dump(data, outf)
