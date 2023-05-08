import os
import shutil
from contextlib import contextmanager
import random
from pathlib import Path
from rich.progress import track
from twinspect.globals import console


__all__ = [
    "random_seed",
    "Graph",
    "clusterize",
    "iter_files",
]


@contextmanager
def random_seed(seed):
    # type: (int) -> None
    """
    Context manager for setting the random seed temporarily.

    :param seed: The seed value to use for random number generation.
    """
    old_state = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(old_state)


def iter_files(path: Path):
    """Iterate all files in path recurively with deterministic ordering"""
    for root, dirs, files in os.walk(path, topdown=False):
        dirs.sort()
        files.sort()
        for filename in files:
            yield Path(os.path.join(root, filename))


def clusterize(src: Path, dst: Path, clusters: int):
    """Copy files from source to destination into a cluster folder structure."""
    clustered = 0
    files = [fp for fp in iter_files(src) if fp.is_file()]
    for path in track(files, description=f"Clusterizing {dst.name}", console=console):
        if clustered < clusters:
            cluster_folder_name = f"{clustered:07d}"
            target_dir = dst / cluster_folder_name
            target_dir.mkdir(parents=True)
            target_file = target_dir / f"0{path.name}"
            shutil.copy(path, target_file)
            # log.trace(f"{path.name} -> {cluster_folder_name}/{target_file.name}")
            clustered += 1
        else:
            shutil.copy(path, dst)


class Graph:
    def __init__(self):
        self.adj_list = {}

    def add_edge(self, a, b):
        if a not in self.adj_list:
            self.adj_list[a] = set()
        self.adj_list[a].add(b)

        if b not in self.adj_list:
            self.adj_list[b] = set()
        self.adj_list[b].add(a)

    def connected_components(self):
        visited = set()
        components = []

        for node in self.adj_list:
            if node not in visited:
                component = set()
                self._dfs(node, visited, component)
                components.append(component)

        return components

    def _dfs(self, node, visited, component):
        visited.add(node)
        component.add(node)
        for neighbor in self.adj_list[node]:
            if neighbor not in visited:
                self._dfs(neighbor, visited, component)
