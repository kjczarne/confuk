import re
import toml
import json
from typing import *
from inspect import signature
from pydantic import BaseModel
from pathlib import Path
from easydict import EasyDict as edict
from omegaconf import OmegaConf, DictConfig as OmegaConfigDict
from ruamel.yaml import YAML
from copy import deepcopy

CfgClass = Type[Any]
PydanticCfgClass = Type[BaseModel]
ConfigDict = Dict[str, Any]
SupportedCfgLiterals = Literal[
    "dict", "d"
    "attr", "edict", "ed"
    "omega", "omegaconf", "o"
]
SupportedConfigFormat = SupportedCfgLiterals | CfgClass | PydanticCfgClass | None


def _build_repl_dict(config_file_path: Path) -> Dict[str, Any]:
    """Builds a dict of variable replacements that are built into the config loader.
    Two formats are supported: `$something` (older) and `${something}` (newer, recommended).
    """
    repls = {
        "$this_file": config_file_path,
        "$this_dir": config_file_path.parent,
        "$this_dirname": config_file_path.parent.name,
        "$this_filename": config_file_path.name,
        "$this_filename_stem": config_file_path.stem,
        "$this_filename_suffix": config_file_path.suffix.replace(".", ""),
        "$cwd": Path.cwd()
    }
    repls_with_curly_braces = {"${" + f"{k.replace('$', '')}" + "}": v for k, v in repls.items()}
    repls.update(repls_with_curly_braces)
    return repls


def _variable_interpolation(ipt: str, key: str, repl_dict: Dict[str, Any]):
    """Performs a basic variable interpolation by replacing the key with a value
    picked out from a provided dictionary.
    """
    if key in repl_dict.keys():
        return ipt.replace(key, str(repl_dict[key]))
    raise KeyError(f"{key} not found in the dictionary provided. Keys that exist: {tuple(repl_dict.keys())}")


def _handle_import_path(config_file_path_path: Path, import_path: Path | str) -> Path:
    repls = _build_repl_dict(config_file_path_path)
    for key in repls.keys():
        import_path = _variable_interpolation(import_path, key, repls)
    if import_path == config_file_path_path:
        raise ValueError("Import path cannot be the same as the current file")
    return Path(import_path)


def _handle_imports(imports_list: List[Path]) -> ConfigDict:
    out = {}
    for import_ in imports_list:
        import_dict = _parse_config_dict(import_)
        out.update(import_dict)
    return out


def _recursive_dict_update(d: ConfigDict, u: ConfigDict) -> ConfigDict:
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = _recursive_dict_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def _handle_preamble(config_dict: ConfigDict, config_file_path: Path) -> ConfigDict:
    if "pre" in config_dict.keys():
        pre = config_dict["pre"]
        if "imports" in pre.keys():
            imports = pre["imports"]
            imports_ = []
            for value in imports:
                imports_.append(_handle_import_path(config_file_path, value))
            # At this point `imports` contains actual paths
            cfg_dict_from_imports = _handle_imports(imports_)
            # Override values from imports with those from the `config_dict`:
            cfg_dict_from_imports = _recursive_dict_update(cfg_dict_from_imports, config_dict)
            return cfg_dict_from_imports
        return config_dict
    return config_dict


def _remove_preamble(config_dict: ConfigDict) -> ConfigDict:
    if "pre" in config_dict.keys():
        del config_dict["pre"]
    return config_dict


# def replacer(config_dict: ConfigDict, old_value: Any, new_value: Any):
#     # If we want to switch to just string replacements from recursion,
#     # we can use this function:
#     config_str = json.dumps(config_dict)
#     config_str = config_str.replace(old_value, str(new_value))
#     print(config_str)
#     return json.loads(config_str)


def replacer(config_dict: ConfigDict, old_value: Any, new_value: Any):
    match config_dict:
        case dict(config_dict):
            return {k: replacer(v, old_value, new_value) for k, v in config_dict.items()}
        case list(config_dict):
            return [replacer(v, old_value, new_value) for v in config_dict]
        case str(config_dict):
            return config_dict.replace(old_value, str(new_value))
        case _:
            return config_dict


def _interpolate_special_variables(config_dict: ConfigDict, config_path: Path):
    repls = _build_repl_dict(config_path)
    config_dict_ = deepcopy(config_dict)
    for k, v in repls.items():
        config_dict_ = replacer(config_dict_, k, v)
    return config_dict_


def _handle_variable_interpolation(config_dict: ConfigDict, config_path: Path):
    # Lazy, but we borrow this from `omegaconf`, which is
    # the most brilliant package for configuration and
    # we support it as an output, so might as well use
    # existing solutions to old problems, except we need to
    # interpolate a couple of our own tags:
    config = _interpolate_special_variables(config_dict, config_path)
    config = OmegaConfigDict(config)
    config = OmegaConf.create(config)
    config = OmegaConf.to_container(config, resolve=True)
    return config


def _parse_toml(config_file_path: Path) -> ConfigDict:
    with open(config_file_path, 'r') as file:
        cfg = toml.load(file)
    return cfg


def _parse_yaml(config_file_path: Path) -> ConfigDict:
    yaml = YAML(typ="safe")
    with open(config_file_path, "r") as f:
        yaml_str = f.read()
        cfg = yaml.load(yaml_str)
    return cfg


def _parse_json(config_file_path: Path) -> ConfigDict:
    with open(config_file_path, "r") as f:
        cfg = json.load(f)
    return cfg


def _parse_config_dict(config_file_path: Path) -> ConfigDict:

    match config_file_path.suffix.lower():
        case ".toml":
            config_dict = _parse_toml(config_file_path)
        case ".yaml":
            config_dict = _parse_yaml(config_file_path)
        case ".json":
            config_dict = _parse_json(config_file_path)
        case _:
            if not config_file_path.exists():
                raise ValueError(f"{config_file_path} does not exist")
            raise ValueError(f"{config_file_path.suffix.upper()} config format is not supported")

    config_dict = _handle_preamble(config_dict, config_file_path)
    config_dict = _remove_preamble(config_dict)
    config_dict = _handle_variable_interpolation(config_dict, config_file_path)
    return config_dict


def _dict_to_kwarg_constructor(config_dict: ConfigDict, cfg_class: CfgClass) -> CfgClass:
    config = cfg_class(**config_dict)
    return config


def _parse_config_kwarg_constructor(config_file_path: Path, cfg_class: CfgClass) -> CfgClass:
    config_dict = _parse_config_dict(config_file_path)
    return _dict_to_kwarg_constructor(config_dict, cfg_class)


def _dict_to_pydantic(config_dict: ConfigDict, cfg_class: CfgClass) -> CfgClass:
    return _dict_to_kwarg_constructor(config_dict, cfg_class)


def _parse_config_pydantic(config_file_path: Path, cfg_class: PydanticCfgClass) -> BaseModel:
    return _parse_config_kwarg_constructor(config_file_path, cfg_class)


def _dict_to_easydict(config_dict: ConfigDict) -> edict:
    return edict(config_dict)


def _parse_config_easydict(config_file_path: Path) -> edict:
    config_dict = _parse_config_dict(config_file_path)
    return _dict_to_easydict(config_dict)


def _dict_to_omegaconfig(config_dict: ConfigDict) -> OmegaConfigDict:
    return OmegaConf.create(config_dict)


def _parse_omegaconfig(config_file_path: Path) -> OmegaConfigDict:
    config_dict = _parse_config_dict(config_file_path)
    return _dict_to_omegaconfig(config_dict)


def parse_config(config_file_path_or_dict: Path | ConfigDict, cfg_class: SupportedConfigFormat = None):
    """Takes a path object to a toml file and returns a config object.

    Args:
        config_file_path (Path | ConfigDict): path to the toml file or an existing `ConfigDict` instance
        cfg_class (SupportedConfigFormat, optional): config loader class. Defaults to None.
            If set to `"attr"`, the config will be loaded as an `easydict` object instead
            of a conventional dictionary.

    Returns:
        An instance of the class used to load the config
    """

    def _handle_dict_or_path(config_file_path_or_dict: Path | ConfigDict,
                             dict_fn: Callable[[ConfigDict], Any],
                             parse_fn: Callable[[Path, Any], Any] | Callable[[Path], Any]):
        """Prepares a function to call depending on whether the input is a dictionary
        of an existing config to be updated/post-processed, or a path to a config file
        that has not been parsed yet.

        Args:
            config_file_path_or_dict (Path | ConfigDict): path to the config file or config dict
            dict_fn (Callable): a function that converts a config dict to a desired output type
            parse_fn (Callable): a function that parses a config file

        Raises:
            TypeError: If the signature of either of he functions is incorrect

        Returns:
            Any: desired config instance of a chosen type (dict, class, etc.)
        """
        match config_file_path_or_dict:
            case Path():
                # There are two kinds of signatures here, one which accepts `cfg_class`
                # and one which doesn't
                num_params_for_parse_fn = len(signature(parse_fn).parameters)
                match num_params_for_parse_fn:
                    case 2:
                        return parse_fn(config_file_path_or_dict, cfg_class)
                    case 1:
                        return parse_fn(config_file_path_or_dict)
                    case _:
                        raise TypeError(f"Function {parse_fn.__name__} has {num_params_for_parse_fn}, this type of signature is unsupported.")
            case dict(config_file_path_or_dict):
                return dict_fn(config_file_path_or_dict)

    match cfg_class:
        case None | "dict" | "d":
            return _handle_dict_or_path(config_file_path_or_dict, dict, _parse_config_dict)
        case "attr" | "edict" | "ed":
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_easydict, _parse_config_easydict)
        case "omega" | "omegaconf" | "o":
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_omegaconfig, _parse_omegaconfig)
        case BaseModel():
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_pydantic, _parse_config_pydantic)
        case _:
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_kwarg_constructor, _parse_config_kwarg_constructor)
