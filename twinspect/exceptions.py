from pathlib import Path

__all__ = [
    "IntegrityError",
    "EmptyFileError",
    "DuplicateFileError",
]


class IntegrityError(Exception):
    def __init__(self, path, expected_hash, actual_hash):
        # type: (str|Path, str, str) -> None
        self.path = path
        self.expected = expected_hash
        self.actual = actual_hash

    def __str__(self):
        return f"IntegrityError: {self.path} expected hash {self.expected}, but got {self.actual}"


class EmptyFileError(Exception):
    def __init__(self, path):
        # type: (str|Path) -> None
        self.path = path

    def __str__(self):
        return f"EmptyFileError: {self.path}"


class DuplicateFileError(Exception):
    def __init__(self, file_a, file_b):
        # type: (str|Path, str|Path) -> None
        self.file_a = file_a
        self.file_b = file_b

    def __str__(self):
        return f"DuplicateFileError: {self.file_a} == {self.file_b}"
