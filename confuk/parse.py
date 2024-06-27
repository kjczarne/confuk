import toml
from typing import Type, Any, Literal, Dict, List
from pydantic import BaseModel
from pathlib import Path
from easydict import EasyDict as edict

CfgClass = Type[Any]
PydanticCfgClass = Type[BaseModel]


def _handle_import_path(toml_file_path: Path, import_path: Path | str) -> Path:
    repls = {
        "$this_file": toml_file_path,
        "$this_dir": toml_file_path.parent,
        "$cwd": Path.cwd()
    }
    for key, value in repls.items():
        import_path = Path(str(import_path).replace(key, str(value)))
    if import_path == toml_file_path:
        raise ValueError("Import path cannot be the same as the current file")
    return import_path


def _handle_imports(imports_list: List[Path]) -> Dict[str, Any]:
    out = {}
    for import_ in imports_list:
        import_dict = _parse_config_dict(import_)
        out.update(import_dict)
    return out


def _recursive_dict_update(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = _recursive_dict_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def _handle_preamble(config_dict: Dict[str, Any], toml_file_path: Path) -> Dict[str, Any]:
    if "pre" in config_dict.keys():
        pre = config_dict["pre"]
        if "imports" in pre.keys():
            imports = pre["imports"]
            imports_ = []
            for value in imports:
                imports_.append(_handle_import_path(toml_file_path, value))
            # At this point `imports` contains actual paths
            cfg_dict_from_imports = _handle_imports(imports_)
            # Override values from imports with those from the `config_dict`:
            cfg_dict_from_imports = _recursive_dict_update(cfg_dict_from_imports, config_dict)
            return cfg_dict_from_imports
        return config_dict
    return config_dict


def _remove_preamble(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    if "pre" in config_dict.keys():
        del config_dict["pre"]
    return config_dict


def _parse_config_dict(toml_file: Path):
    with open(toml_file, 'r') as file:
        config_dict = toml.load(file)
        config_dict = _handle_preamble(config_dict, toml_file)
        config_dict = _remove_preamble(config_dict)
        return config_dict


def _parse_config_kwarg_constructor(toml_file: Path, cfg_class: CfgClass):
    config_dict = _parse_config_dict(toml_file)
    config = cfg_class(**config_dict)
    return config


def _parse_config_pydantic(toml_file: Path, cfg_class: PydanticCfgClass):
    return _parse_config_kwarg_constructor(toml_file, cfg_class)


def _parse_config_easydict(toml_file: Path):
    config_dict = _parse_config_dict(toml_file)
    return edict(config_dict)


def parse_config(toml_file: Path, cfg_class: CfgClass | Literal["attr"] | None = None):
    """Takes a path object to a toml file and returns a config object.

    Args:
        toml_file (Path): path to the toml file
        cfg_class (CfgClass | Literal["attr"], optional): config loader class. Defaults to None.
            If set to `"attr"`, the config will be loaded as an `easydict` object instead
            of a conventional dictionary.

    Returns:
        An instance of the class used to load the config
    """
    match cfg_class:
        case None:
            return _parse_config_dict(toml_file)
        case "attr":
            return _parse_config_easydict(toml_file)
        case BaseModel():
            return _parse_config_pydantic(toml_file, cfg_class)
        case _:
            return _parse_config_kwarg_constructor(toml_file, cfg_class)
