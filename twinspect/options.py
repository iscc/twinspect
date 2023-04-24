# -*- coding: utf-8 -*-
"""Framework Evironment options"""
import yaml
from pydantic import BaseSettings, Field, DirectoryPath, FilePath, validator
import twinspect as ts
from pathlib import Path


__all__ = ["opts", "cnf"]


class TwinSpectSettings(BaseSettings):
    """Evaluation framework environment configuration"""

    class Config:
        validate_assignment = True
        env_file = ".env"

    root_folder: DirectoryPath = Field(
        ts.DEFAULT_ROOT_FOLDER, description="Root directory for all evaluation data"
    )
    config_file: FilePath = Field(
        ts.DEFAULT_CONFIG_FILE, description="Benchmark configuration YML file"
    )

    @validator("root_folder", pre=True)
    def create_root_folder(cls, value):
        """Create root_folder if it does not exist."""
        path = Path(value)
        path.mkdir(parents=True, exist_ok=True)
        return path


opts = TwinSpectSettings()
cnf = ts.Configuration.parse_obj(yaml.safe_load(open(opts.config_file)))

