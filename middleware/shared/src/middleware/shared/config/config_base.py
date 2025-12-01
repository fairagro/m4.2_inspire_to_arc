"""FAIRagro Middleware base configuration module."""

import logging
from pathlib import Path
from typing import Annotated, Literal, TypeVar

from pydantic import BaseModel, Field

from .config_wrapper import ConfigWrapper

T = TypeVar("T", bound="ConfigBase")


class ConfigBase(BaseModel):
    """Configuration base class for the FAIRagro advanced Middleware."""

    log_level: Annotated[
        Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"], Field(description="Logging level")
    ] = "INFO"

    @classmethod
    def from_config_wrapper(cls: type[T], wrapper: ConfigWrapper) -> T:
        """Create Config from ConfigWrapper.

        Args:
            wrapper (ConfigWrapper): Wrapped configuration data.

        Returns:
            T: An instance of the specific ConfigBase subclass.

        """
        unwrapped = wrapper.unwrap()
        return cls.model_validate(unwrapped)

    @classmethod
    def from_data(cls: type[T], data: dict) -> T:
        """Create Config from raw data dictionary.

        Args:
            data (dict): Raw configuration data.

        Returns:
            T: An instance of the specific ConfigBase subclass.

        """
        wrapper = ConfigWrapper.from_data(data)
        return cls.from_config_wrapper(wrapper)

    @classmethod
    def from_yaml_file(cls: type[T], path: Path) -> T:
        """Create Config from a YAML file.

        Args:
            path (Path): Path to the YAML config file.

        Returns:
            T: An instance of the specific ConfigBase subclass.

        Raises:
            RuntimeError: If the config file is not found.

        """
        if path.is_file():
            wrapper = ConfigWrapper.from_yaml_file(path)
            return cls.from_config_wrapper(wrapper)
        msg = f"Config file {path} not found."
        logging.error(msg)
        raise RuntimeError(msg)
