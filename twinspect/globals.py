"""Global values"""
from loguru import logger as log
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

__all__ = [
    "log",
    "console",
    "progress",
]

console = Console()


def _log_formatter(record: dict) -> str:
    """Log message formatter"""
    color_map = {
        "TRACE": "blue",
        "DEBUG": "cyan",
        "INFO": "bold",
        "SUCCESS": "bold green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "CRITICAL": "bold white on red",
    }
    lvl_color = color_map.get(record["level"].name, "cyan")
    return (
        "[not bold green]{time:YYYY/MM/DD HH:mm:ss}[/not bold green] | {module:<12} | {level.icon}"
        + f"  - [{lvl_color}]{{message}}[/{lvl_color}]"
    )


log.remove()
log.add(
    console.print,
    level="TRACE",
    format=_log_formatter,
    colorize=True,
)


progress = Progress(
    TextColumn("[bold blue]{task.fields[name]}", justify="right"),
    BarColumn(),
    "[progress.percentage]{task.percentage:>3.1f}%",
    "•",
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
    console=console,
)
