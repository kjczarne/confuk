import toml
from typing import Type, Any
from pydantic import BaseModel
from pathlib import Path

CfgClass = Type[Any]
PydanticCfgClass = Type[BaseModel]


def _parse_config_dict(toml_file: Path):
    with open(toml_file, 'r') as file:
        config_dict = toml.load(file)
        return config_dict


def _parse_config_kwarg_constructor(toml_file: Path, cfg_class: CfgClass):
    config_dict = _parse_config_dict(toml_file)
    config = cfg_class(**config_dict)
    return config


def _parse_config_pydantic(toml_file: Path, cfg_class: PydanticCfgClass):
    return _parse_config_kwarg_constructor(toml_file, cfg_class)


def parse_config(toml_file: Path, cfg_class: CfgClass | None = None):
    """Takes a path object to a toml file and returns a config object.

    Args:
        toml_file (Path): path to the toml file
        cfg_class (CfgClass, optional): config loader class. Defaults to None.

    Returns:
        An instance of the class used to load the config
    """
    match cfg_class:
        case None:
            return _parse_config_dict(toml_file)
        case BaseModel():
            return _parse_config_pydantic(toml_file, cfg_class)
        case _:
            return _parse_config_kwarg_constructor(toml_file, cfg_class)
