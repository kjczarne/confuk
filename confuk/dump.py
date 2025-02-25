import json
import jsonpickle
import pickle
import toml
from omegaconf import DictConfig as OmegaConfDictConfig, OmegaConf
from ruamel.yaml import YAML
from .parse import ConfigDict
from pathlib import Path

SupportedDumpFormats = [
    "json",
    "yaml",
    "toml"
]

def _dump_toml(config: ConfigDict, dump_path: Path):
    with open(dump_path, 'w') as f:
        toml.dump(config, f)


def _dump_yaml(config: ConfigDict, dump_path: Path):
    yaml = YAML(typ="safe")
    with open(dump_path, "w") as f:
        yaml.dump(config, f)


def _dump_json(config: ConfigDict, dump_path: Path):
    with open(dump_path, "w") as f:
        json.dump(config, f)


def _dump_jsonpickle(config: ConfigDict, dump_path: Path):
    with open(dump_path, "w") as f:
        f.write(jsonpickle.encode(config))


def _dump_pickle(config: ConfigDict, dump_path: Path):
    with open(dump_path, "wb") as f:
        pickle.dump(config, f)


def _omegaconf_container(config: OmegaConfDictConfig) -> ConfigDict:
    return OmegaConf.to_container(config, resolve=True)


def dump_config(config: ConfigDict, path: Path | str, create_parents: bool = True):

    if isinstance(path, str):
        path = Path(path)

    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(config, OmegaConfDictConfig):
        config = _omegaconf_container(config)

    match path.suffix.lower():
        case ".json":
            _dump_json(config, path)
        case ".jsonp":
            _dump_jsonpickle(config, path)
        case ".pkl":
            _dump_pickle(config, path)
        case ".toml":
            _dump_toml(config, path)
        case ".yaml":
            _dump_yaml(config, path)
        case _:
            raise TypeError(f"Extension {path.suffix} not supported. Supported dump file formats are {SupportedDumpFormats}")
