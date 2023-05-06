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
    Efficient ANNS Search Engine
    """

    def __init__(self, csv_path, code_field="code"):
        # type: (Path|str, str) -> None
        """
        Cached initialization from a CSV-file which must have a hex coded comapct binary codes in
        the `code_field` column.
        """
        c = Path(csv_path)
        self.csv_path = c
        self.code_field = code_field
        self.index_file = c.parent / f"{c.stem}.anns"
        self.index: IndexBinaryHNSW | None = None
        self.numpy_codes: NDArray[np.uint8] | None = None
        self.load()

    def iter_queries(self, threshold, nprobe=10):
        # type: (int, int) -> Iterable[NDArray[np.uint8]]
        """Iterate over all pairs query results with hamming `threshold`"""
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

    def load(self):
        """Load or build index"""
        # Load query codes from CSV
        self.load_csv()

        # Load existing index
        if self.index_file.exists():
            self.index = read_index_binary(self.index_file.as_posix())
            return

        # Build & Store  FAISS Binary HNSW index
        bit_length = len(self.numpy_codes[0]) * 8
        log.debug(f"Build HNSQ index {self.index_file.name} (bit length {bit_length})")
        self.index = IndexBinaryHNSW(bit_length)
        self.index.verbose = True
        self.index.train(self.numpy_codes)
        self.index.add(self.numpy_codes)
        self.save()

    def save(self):
        """Save index to disk"""
        write_index_binary(self.index, self.index_file.as_posix())

    def load_csv(self):
        # type: () -> NDArray[np.uint8]
        # Load codes from csv to numpy array
        log.debug(f"Loading codes from {self.csv_path.name}")
        with open(self.csv_path, "r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")
            # Extract the hex encoded compact binary codes from the specified column
            hex_codes = [row[self.code_field] for row in reader]
            # Convert hex codes to np.uint8 arrays
            uint8_arrays = [
                np.array(
                    [np.uint8(int(hex_code[i : i + 2], 16)) for i in range(0, len(hex_code), 2)]
                )
                for hex_code in hex_codes
            ]
            # Create a 2-dimensional numpy array
            uint8_matrix = np.stack(uint8_arrays, axis=0)
        self.numpy_codes = uint8_matrix
        return uint8_matrix
