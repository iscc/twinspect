# -*- coding: utf-8 -*-
from pydantic import BaseSettings, Field, DirectoryPath
import twinspect as ts


__all__ = ["cnf"]


class TwinSpectSettings(BaseSettings):
    """Evaluation framework environment configuration"""

    class Config:
        validate_assignment = True
        env_file = ".env"

    root_folder: DirectoryPath = Field(
        ts.DEFAULT_ROOT_FOLDER, description="Root directory for all evaluation data"
    )

cnf = TwinSpectSettings()
