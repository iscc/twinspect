# -*- coding: utf-8 -*-
from pathlib import Path
from twinspect.models import Dataset


def install(dataset):
    # type: (Dataset) -> Path
    """Noop - for private/commercial test data"""
    return dataset.data_folder
