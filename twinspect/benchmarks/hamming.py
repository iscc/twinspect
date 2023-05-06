"""
The TwinSpect Benchmark requires an all-pairs hamming distance search which unfortunately
does not scale for larger datasets above a couple of thousand items O(n^2). So instead we use a
less accurate but much more performant Approximate Nearest Neighbor Search (ANNS) based on the
faiss library.
"""
import csv
from typing import Iterable
from numpy.typing import NDArray
import numpy as np
from loguru import logger as log
from pathlib import Path
from faiss import IndexBinaryHNSW, read_index_binary, write_index_binary


__all__ = ["HammingHero"]


class HammingHero:
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
