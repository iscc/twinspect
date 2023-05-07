from contextlib import contextmanager
import random

__all__ = [
    "random_seed",
    "Graph",
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
