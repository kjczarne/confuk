import toml
from typing import Type, Any, Literal, Dict, List
from pydantic import BaseModel
from pathlib import Path
from easydict import EasyDict as edict
from omegaconf import OmegaConf, DictConfig as OmegaConfigDict

CfgClass = Type[Any]
PydanticCfgClass = Type[BaseModel]
ConfigDict = Dict[str, Any]
SupportedCfgLiterals = Literal[
    "dict", "d"
    "attr", "edict", "ed"
    "omega", "omegaconf", "o"
]


def _build_repl_dict(toml_file_path: Path) -> Dict[str, Any]:
    """Builds a dict of variable replacements that are built into the config loader.
    Two formats are supported: `$something` (older) and `${something}` (newer, recommended).
    """
    repls = {
        "$this_file": toml_file_path,
        "$this_dir": toml_file_path.parent,
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


def _handle_import_path(toml_file_path: Path, import_path: Path | str) -> Path:
    repls = _build_repl_dict(toml_file_path)
    for key in repls.keys():
        import_path = _variable_interpolation(import_path, key, repls)
    if import_path == toml_file_path:
        raise ValueError("Import path cannot be the same as the current file")
    return import_path


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


def _handle_preamble(config_dict: ConfigDict, toml_file_path: Path) -> ConfigDict:
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


def _remove_preamble(config_dict: ConfigDict) -> ConfigDict:
    if "pre" in config_dict.keys():
        del config_dict["pre"]
    return config_dict


def _handle_variable_interpolation(config_dict: ConfigDict):
    # Lazy, but we borrow this from `omegaconf`, which is
    # the most brilliant package for configuration and
    # we support it as an output, so might as well use
    # existing solutions to old problems:
    config_odict = OmegaConfigDict(config_dict)
    config = OmegaConf.create(config_odict)
    return OmegaConf.to_container(config, resolve=True)


def _parse_config_dict(toml_file: Path) -> ConfigDict:
    with open(toml_file, 'r') as file:
        config_dict = toml.load(file)
        config_dict = _handle_preamble(config_dict, toml_file)
        config_dict = _remove_preamble(config_dict)
        config_dict = _handle_variable_interpolation(config_dict)
        return config_dict


def _parse_config_kwarg_constructor(toml_file: Path, cfg_class: CfgClass) -> CfgClass:
    config_dict = _parse_config_dict(toml_file)
    config = cfg_class(**config_dict)
    return config


def _parse_config_pydantic(toml_file: Path, cfg_class: PydanticCfgClass) -> BaseModel:
    return _parse_config_kwarg_constructor(toml_file, cfg_class)


def _parse_config_easydict(toml_file: Path) -> edict:
    config_dict = _parse_config_dict(toml_file)
    return edict(config_dict)


def _parse_omegaconfig(toml_file: Path) -> OmegaConf:
    config_dict = _parse_config_dict(toml_file)
    return OmegaConf.create(config_dict)


def parse_config(toml_file: Path, cfg_class: CfgClass | SupportedCfgLiterals | None = None):
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
        case None | "dict" | "d":
            return _parse_config_dict(toml_file)
        case "attr" | "edict" | "ed":
            return _parse_config_easydict(toml_file)
        case "omega" | "omegaconf" | "o":
            return _parse_omegaconfig(toml_file)
        case BaseModel():
            return _parse_config_pydantic(toml_file, cfg_class)
        case _:
            return _parse_config_kwarg_constructor(toml_file, cfg_class)
