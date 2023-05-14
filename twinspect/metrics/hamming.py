"""
The TwinSpect Benchmark requires an all-pairs hamming distance search which unfortunately
does not scale for larger datasets above a couple of thousand items O(n^2). So instead we use a
less accurate but much more performant Approximate Nearest Neighbor Search (ANNS) based on the
faiss library.

TODO: Use LameDuck with progress output for smaller datesets up to 1000 queries.
"""
import csv
from typing import Iterable
from numpy.typing import NDArray
import numpy as np
import pandas as pd
from loguru import logger as log
from pathlib import Path
from faiss import IndexBinaryHNSW, read_index_binary, write_index_binary
from rich.progress import track
from twinspect.globals import console
from collections import Counter


__all__ = ["HammingHero", "LameDuck"]


class BaseHammingSearch:
    def _load_csv(self):
        # type: () -> NDArray[np.uint8]
        """
        Load codes from csv to numpy array and returns the numpy array.

        :return: 2-dimensional numpy array of binary codes.
        """
        # Load codes from csv to numpy array
        log.debug(f"Loading codes from {self.csv_path.name}")
        with self.csv_path.open("r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")
            hex_codes = [row[self.code_field] for row in reader]

        num_codes = len(hex_codes)
        code_length = len(hex_codes[0]) // 2
        uint8_matrix = np.empty((num_codes, code_length), dtype=np.uint8)
        for i, hex_code in enumerate(hex_codes):
            for j in range(0, len(hex_code), 2):
                uint8_matrix[i, j // 2] = np.uint8(int(hex_code[j : j + 2], 16))

        self.numpy_codes = uint8_matrix
        return uint8_matrix


class LameDuck(BaseHammingSearch):
    """
    Brute force all-pairs based exact NNS Search that also collects all-pairs hamming distribution.
    """

    def __init__(self, csv_path, code_field="code"):
        # type: (Path|str, str) -> None
        """
        Cached initialization from a CSV-file which must have a hex coded comapct binary codes in
        the `code_field` column.

        :param csv_path: Path to the CSV file containing hex coded compact binary codes.
        :param code_field: Column name containing the binary codes.
        """
        c = Path(csv_path)
        self.csv_path = c
        self.code_field = code_field
        self.numpy_codes: NDArray[np.uint8] | None = None
        self.distribution = Counter()
        self._load_csv()

    def compute_queries(self, threshold):
        # type: (int) -> pd.DataFrame
        """
        Collect query results into a DataFrame of the form:

            id                                       query_result
        0    0  [(0, 4), (0, 5), (0, 7), (0, 8), (0, 9), (1, 1...
        1    1  [(1, 10), (2, 0), (2, 3), (2, 4), (2, 5), (2, ...

        :param threshold: Hamming distance threshold for the search.
        :return: DataFrame with ids and query results
        """
        query_results = []
        for item in track(
            self.iter_queries(threshold), total=len(self.numpy_codes), console=console
        ):
            query_results.append(item)
        df = pd.DataFrame({"id": range(len(query_results)), "query_result": query_results})
        return df

    def iter_queries(self, threshold):
        # type: (int) -> Iterable[NDArray[np.uint8]]
        """
        Iterate over all pairs query results with hamming `threshold`.

        :param threshold: Hamming distance threshold for the search.
        """
        for i, code in enumerate(self.numpy_codes):
            query_result = []
            for j, other_code in enumerate(self.numpy_codes):
                if i != j:
                    distance = self.hamming_distance(code, other_code)
                    self.distribution.update([distance])
                    if distance <= threshold:
                        query_result.append((distance, j))
            query_result.sort()
            yield query_result

    @staticmethod
    def hamming_distance(code1, code2):
        # type: (NDArray[np.uint8], NDArray[np.uint8]) -> int
        """
        Calculate the Hamming distance between two binary codes.

        :param code1: Binary code 1.
        :param code2: Binary code 2.
        :return: Hamming distance.
        """
        return int(np.sum(np.unpackbits(code1 ^ code2)))


class HammingHero(BaseHammingSearch):
    """
    Efficient ANNS Search Engine based on the Faiss library.
    """

    def __init__(self, csv_path, code_field="code"):
        # type: (Path|str, str) -> None
        """
        Cached initialization from a CSV-file which must have a hex coded comapct binary codes in
        the `code_field` column.

        :param csv_path: Path to the CSV file containing hex coded compact binary codes.
        :param code_field: Column name containing the binary codes.
        """
        c = Path(csv_path)
        self.csv_path = c
        self.code_field = code_field
        self.index_file = c.parent / f"{c.stem}.anns"
        self.index: IndexBinaryHNSW | None = None
        self.numpy_codes: NDArray[np.uint8] | None = None
        self._load()

    def compute_queries(self, threshold, nprobe=10):
        # type: (int, int) -> pd.DataFrame
        """
        Collect query results into a DataFrame of the form:

            id                                       query_result
        0    0  [(0, 4), (0, 5), (0, 7), (0, 8), (0, 9), (1, 1...
        1    1  [(1, 10), (2, 0), (2, 3), (2, 4), (2, 5), (2, ...

        :param threshold: Hamming distance threshold for the search.
        :param nprobe: Number of probes to use during the search.
        :return: DataFrame with ids and query results
        """
        query_results = list(self.iter_queries(threshold, nprobe))
        df = pd.DataFrame({"id": range(len(query_results)), "query_result": query_results})
        return df

    def iter_queries(self, threshold, nprobe=10):
        # type: (int, int) -> Iterable[NDArray[np.uint8]]
        """
        Iterate over all pairs query results with hamming `threshold`.

        :param threshold: Hamming distance threshold for the search.
        :param nprobe: Number of probes to use during the search.
        """
        index: IndexBinaryHNSW = self.index
        index.nprobe = nprobe
        for i, code in enumerate(self.numpy_codes):
            query_code = np.expand_dims(code, axis=0)
            distances, indices = index.search(query_code, threshold)
            query_result = [
                (dist, idx)
                for dist, idx in zip(distances[0], indices[0])
                if dist <= threshold and idx != i
            ]
            query_result.sort()
            yield query_result

    def _load(self):
        # type: () -> None
        """
        Load or build index.
        """
        # Load query codes from CSV
        self._load_csv()

        # Load existing index
        if self.index_file.exists():
            log.debug(f"Load HNSW index {self.index_file.name}")
            self.index = read_index_binary(self.index_file.as_posix())
            return

        # Build & Store  FAISS Binary HNSW index
        log.debug(f"Build HNSW index {self.index_file.name}")
        bit_length = len(self.numpy_codes[0]) * 8
        self.index = IndexBinaryHNSW(bit_length)
        self.index.train(self.numpy_codes)
        self.index.add(self.numpy_codes)
        self._save()

    def _save(self):
        # type: () -> None
        """
        Save index to disk.
        """
        write_index_binary(self.index, self.index_file.as_posix())
