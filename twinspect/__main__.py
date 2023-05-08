"""
TwinSpect benchmark CLI & main entrypoint.

High Level Processing Pipeline:

1. Read Configuration: Load Yaml-based benchmark configuration file
2. Algorithm Acquisition: Install dependencies required to run algorithms
3. Dataset Aquisition Pipline: Download/Clusterize/Transform
4. Media File Processing: Process media files for each configured/active algo/dataset pair
5. Algorithm Benchmarking: Calculate benchmarking metrics from media processing results
6. Build Benchmark Result: Create/update Markdown/HTML output of benchmarking results
"""
from typing import Optional
import typer
from typer import Argument, Option
from typing_extensions import Annotated
import twinspect as ts
from pathlib import Path
from loguru import logger as log
from rich.table import Table


HERE = Path(__file__).parent.absolute()
app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def no_command(
    ctx: typer.Context, quiet: bool = Option(False, "-q", "--quiet", help="Suppress logs")
):
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
    if quiet:
        log.remove()


@app.command()
def run():
    """Compute all configured benchmarks."""
    title = f"\n\nTwinSpect v{ts.__version__}"
    typer.echo(title)
    typer.echo("#" * (len(title) + 1))
    typer.echo()
    for benchmark in ts.cnf.active_benchmarks:
        typer.echo()
        log.info(f"Running Benchmark {benchmark.algorithm.name} - {benchmark.dataset.name}")
        benchmark.algorithm.install()
        benchmark.dataset.install()
        benchmark.simprint()  # process media files and create simprint file
        for metric in benchmark.metrics:
            func = ts.load_function(metric.function)
            func(benchmark.simprint())


@app.command()
def version():
    """Show app version"""
    typer.echo(f"TwinSpect v{ts.__version__}")


@app.command(name="hash")
def hash_(folder: Annotated[Optional[Path], Argument()] = None):
    """Compute secure recursive hash for folder"""
    hexhash = ts.check_dir_secure(folder, expected=None, raise_dupes=False)
    typer.echo(hexhash)


@app.command()
def checksum(folder: Annotated[Optional[Path], Argument()] = None):
    """Compute fast recursive checksum for folder"""
    hexhash = ts.check_dir_fast(folder, expected=None, raise_empty=False)
    typer.echo(hexhash)


@app.command()
def algorithms():
    """List available algorithms."""
    table = Table("Label", "Name", "Mode", header_style="on magenta")
    for algo in ts.cnf.algorithms:
        table.add_row(algo.label, algo.name, algo.mode.name)
    ts.console.print(table)
    # c = rich.Console()
    # c.print(table)


@app.command()
def datasets():
    """List available datasets."""
    table = Table("Label", "Name", "Mode", "Samples", "Clusters", header_style="on magenta")
    for ds in ts.cnf.datasets:
        table.add_row(ds.label, ds.name, ds.mode.name, str(ds.samples), str(ds.clusters))
    ts.console.print(table)


@app.command()
def benchmarks():
    """List available benchmarks"""
    table = Table("Algorithm", "Dataset", "Metrics", "Active", header_style="on magenta")
    for b in ts.cnf.benchmarks:
        table.add_row(b.algorithm.name, b.dataset.name, ", ".join(b.metric_labels), str(b.active))
    ts.console.print(table)


@app.command()
def transformations():
    """List available transformations"""
    table = Table("Label", "Name", "Mode", "Parameters", header_style="on magenta")
    for t in ts.cnf.transformations:
        table.add_row(t.label, t.name, t.mode.name, str(t.params))
    ts.console.print(table)


if __name__ == "__main__":
    app()
