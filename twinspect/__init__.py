from pathlib import Path
from loguru import logger
from rich.console import Console

__version__ = "0.1.0"

console = Console()
logger.remove()


def _log_formatter(record: dict) -> str:
    """Log message formatter"""
    color_map = {
        'TRACE': 'blue',
        'DEBUG': 'cyan',
        'INFO': 'bold',
        'SUCCESS': 'bold green',
        'WARNING': 'yellow',
        'ERROR': 'bold red',
        'CRITICAL': 'bold white on red'
    }
    lvl_color = color_map.get(record['level'].name, 'cyan')
    return (
        '[not bold green]{time:YYYY/MM/DD HH:mm:ss}[/not bold green] | {level.icon}'
        + f'  - [{lvl_color}]{{message}}[/{lvl_color}]'
    )


logger.add(
    console.print,
    level='TRACE',
    format=_log_formatter,
    colorize=True,
)

CODE_DIR = Path(__file__).parent.parent.resolve().absolute()
DEFAULT_ROOT_FOLDER = CODE_DIR / "data"
DEFAULT_CONFIG_FILE = CODE_DIR / "config.yml"

from twinspect.schema import Configuration, Dataset, Transformation, Mode, Algorithm, Task
from twinspect.options import *
from twinspect.tools import *

