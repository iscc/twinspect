# -*- coding: utf-8 -*-
"""Framework environment options."""

import yaml
from pathlib import Path
from pydantic import Field, DirectoryPath, FilePath, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import twinspect as ts


__all__ = ["opts", "cnf"]


class TwinSpectSettings(BaseSettings):
    """Evaluation framework environment configuration."""

    model_config = SettingsConfigDict(
        validate_assignment=True,
        env_file=".env",
    )

    root_folder: DirectoryPath = Field(
        default=ts.DEFAULT_ROOT_FOLDER, description="Root directory for all evaluation data"
    )
    config_file: FilePath = Field(
        default=ts.DEFAULT_CONFIG_FILE, description="Benchmark configuration YML file"
    )

    @field_validator("root_folder", mode="before")
    @classmethod
    def create_root_folder(cls, value):
        """Create root_folder if it does not exist."""
        path = Path(value)
        path.mkdir(parents=True, exist_ok=True)
        return path


opts = TwinSpectSettings()
cnf = ts.Configuration.model_validate(yaml.safe_load(open(opts.config_file)))
