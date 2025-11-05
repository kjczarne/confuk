import re
import toml
import json
import importlib.util
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


def _repls_with_lr_delimiters(repls: Dict[str, Any], lr_delimiters: Tuple[str, str] = ("{", "}")):
    l, r = lr_delimiters
    repls_with_curly_braces = {f"${l}" + f"{k.replace('$', '')}" + f"{r}": v for k, v in repls.items()}
    repls.update(repls_with_curly_braces)
    return repls


def _build_repl_dict_without_delimiters(config_file_path: Path) -> Dict[str, Any]:
    resolved_cfg_file_path = config_file_path.resolve()
    return {
        "$this_file": resolved_cfg_file_path,
        "$this_dir": resolved_cfg_file_path.parent,
        "$this_dirname": resolved_cfg_file_path.parent.name,
        "$this_filename": resolved_cfg_file_path.name,
        "$this_filename_stem": resolved_cfg_file_path.stem,
        "$this_filename_suffix": resolved_cfg_file_path.suffix.replace(".", ""),
        "$cwd": Path.cwd()
    }


def _build_repl_dict(config_file_path: Path) -> Dict[str, Any]:
    """Builds a dict of variable replacements that are built into the config loader.
    Two formats are supported: `$something` (older) and `${something}` (newer, recommended).
    """
    repls = _build_repl_dict_without_delimiters(config_file_path)
    return _repls_with_lr_delimiters(repls)


def _build_leaf_repl_dict(config_file_path: Path) -> Dict[str, Any]:
    repls = _build_repl_dict_without_delimiters(config_file_path)
    return _repls_with_lr_delimiters(repls, (r"[", r"]"))


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


def _handle_imports(imports_list: List[Path], skip_variable_interpolation: bool = False) -> ConfigDict:
    out = {}
    for import_ in imports_list:
        import_dict, _ = _parse_config_dict(import_, skip_variable_interpolation)
        out = _recursive_dict_update(out, import_dict)
    return out


def _recursive_dict_update(d: ConfigDict, u: ConfigDict) -> ConfigDict:
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = _recursive_dict_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def _handle_pre_or_postamble(which: Literal["pre", "post"], config_dict: ConfigDict, config_file_path: Path) -> ConfigDict:
    if which in config_dict.keys():
        pre = config_dict[which]
        if "imports" in pre.keys():
            imports = pre["imports"]
            imports_ = []
            for value in imports:
                imports_.append(_handle_import_path(config_file_path, value))
            # At this point `imports` contains actual paths. Note that
            # in `post` we need to defer variable interpolation until the entire config
            # is built up, hence `skip_variable_interpolation=True`
            cfg_dict_from_imports = _handle_imports(imports_, True if which == "post" else False)
            # Override values from imports with those from the `config_dict`:
            cfg_dict_from_imports = _recursive_dict_update(cfg_dict_from_imports, config_dict) if which == "pre" else _recursive_dict_update(config_dict, cfg_dict_from_imports)
            return cfg_dict_from_imports
        return config_dict
    return config_dict


def _remove_pre_or_postamble(which: Literal["pre", "post"], config_dict: ConfigDict) -> ConfigDict:
    if "pre" in config_dict.keys():
        del config_dict["pre"]
    return config_dict


def _handle_preamble(config_dict: ConfigDict, config_file_path: Path) -> ConfigDict:
    return _handle_pre_or_postamble("pre", config_dict, config_file_path)


def _remove_preamble(config_dict: ConfigDict) -> ConfigDict:
    return _remove_pre_or_postamble("pre", config_dict)


def _handle_postamble(config_dict: ConfigDict, config_file_path: Path) -> ConfigDict:
    return _handle_pre_or_postamble("post", config_dict, config_file_path)


def _remove_postamble(config_dict: ConfigDict) -> ConfigDict:
    return _remove_pre_or_postamble("post", config_dict)


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


def _interpolate_special_variables(config_dict: ConfigDict,
                                   config_path: Path,
                                   repl_dict_fn: Callable[[Path], Dict[Any, Any]] = _build_repl_dict):
    repls = repl_dict_fn(config_path)
    config_dict_ = deepcopy(config_dict)
    for k, v in repls.items():
        config_dict_ = replacer(config_dict_, k, v)
    return config_dict_


def _handle_variable_interpolation(config_dict: ConfigDict,
                                   config_path: Path):
    # Lazy, but we borrow this from `omegaconf`, which is
    # the most brilliant package for configuration and
    # we support it as an output, so might as well use
    # existing solutions to old problems, except we need to
    # interpolate a couple of our own tags:
    config = _interpolate_special_variables(config_dict, config_path)

    # Extract parameterized sections after imports are resolved:
    parameterized = _extract_parameterized_sections(config)
    
    # Dict to config instance:
    config = OmegaConfigDict(config)
    config = OmegaConf.create(config)
    config = OmegaConf.to_container(config, resolve=False)

    # Register resolvers:
    _register_parameterized_resolvers(parameterized)

    # Resolve all interpolations
    config = OmegaConf.create(config)
    config = OmegaConf.to_container(config, resolve=True)
    return config


def _handle_leaf_node_interpolation(config_dict: ConfigDict, config_path: Path):
    config = _interpolate_special_variables(config_dict, config_path, _build_leaf_repl_dict)
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


def _parse_python(path: Path) -> tuple[ConfigDict, Callable[[ConfigDict], None] | None]:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None:
        raise ValueError(f"Config {path} could not be imported! Module spec was `None`")
    config_module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ValueError(f"Config {path} could not be imported! Spec loader was `None`")
    spec.loader.exec_module(config_module)
    if not hasattr(config_module, "config"):
        raise TypeError(f"Config module {path} does not have a `config` dictionary. You must declare a `config` variable as a dictionary!")
    cfg_obj = getattr(config_module, "config")
    post_fn = getattr(config_module, "post", None)
    return cfg_obj, post_fn


def _parse_config_dict(config_file_path: Path, skip_variable_interpolation: bool = False) -> ConfigDict:

    match config_file_path.suffix.lower():
        case ".toml":
            config_dict, post_fn = _parse_toml(config_file_path), None
        case ".yaml":
            config_dict, post_fn = _parse_yaml(config_file_path), None
        case ".json":
            config_dict, post_fn = _parse_json(config_file_path), None
        case ".py":
            config_dict, post_fn = _parse_python(config_file_path)
        case _:
            if not config_file_path.exists():
                raise ValueError(f"{config_file_path} does not exist")
            raise ValueError(f"{config_file_path.suffix.upper()} config format is not supported")

    config_dict = _handle_preamble(config_dict, config_file_path)
    config_dict = _remove_preamble(config_dict)
    if not skip_variable_interpolation:
        config_dict = _handle_variable_interpolation(config_dict, config_file_path)
    config_dict = _handle_postamble(config_dict, config_file_path)
    config_dict = _remove_postamble(config_dict)
    # config_dict = _handle_variable_interpolation(config_dict, config_file_path)
    return config_dict, post_fn


def _parse_leaf_config_dict(config_file_path: Path) -> ConfigDict:
    config_dict, post_fn = _parse_config_dict(config_file_path)
    # This interpolates deferred imports and deferred varialbes
    # when we reach the leaf node in the import stack:
    config_dict = _handle_leaf_node_interpolation(config_dict, config_file_path)
    # After the `post` pass, some of the deferred-value variables will
    # not yet be interpolated so we do another pass of `_handle_variable_interpolation`:
    config_dict = _handle_variable_interpolation(config_dict, config_file_path)
    if post_fn is not None:
        post_fn(config_dict)
    return config_dict


def _dict_to_kwarg_constructor(config_dict: ConfigDict, cfg_class: CfgClass) -> CfgClass:
    config = cfg_class(**config_dict)
    return config


def _parse_config_kwarg_constructor(config_file_path: Path, cfg_class: CfgClass) -> CfgClass:
    config_dict = _parse_leaf_config_dict(config_file_path)
    return _dict_to_kwarg_constructor(config_dict, cfg_class)


def _dict_to_pydantic(config_dict: ConfigDict, cfg_class: CfgClass) -> CfgClass:
    return _dict_to_kwarg_constructor(config_dict, cfg_class)


def _parse_config_pydantic(config_file_path: Path, cfg_class: PydanticCfgClass) -> BaseModel:
    return _parse_config_kwarg_constructor(config_file_path, cfg_class)


def _dict_to_easydict(config_dict: ConfigDict) -> edict:
    return edict(config_dict)


def _parse_config_easydict(config_file_path: Path) -> edict:
    config_dict = _parse_leaf_config_dict(config_file_path)
    return _dict_to_easydict(config_dict)


def _dict_to_omegaconfig(config_dict: ConfigDict) -> OmegaConfigDict:
    return OmegaConf.create(config_dict)


def _parse_omegaconfig(config_file_path: Path) -> OmegaConfigDict:
    config_dict = _parse_leaf_config_dict(config_file_path)
    return _dict_to_omegaconfig(config_dict)


def _extract_parameterized_sections(config: Dict[str, Any]) -> Dict[str, tuple]:
    """
    Extract sections with parameters like 'section_name(param1, param2)'.
    
    Returns:
        Dict mapping section names to (params, content) tuples
    """
    parameterized = {}
    pattern = r'^(\w+)\(([\w\s,]+)\)$'
    
    keys_to_remove = []
    for key in list(config.keys()):
        match = re.match(pattern, key)
        if match:
            section_name = match.group(1)
            params_str = match.group(2)
            params = [p.strip() for p in params_str.split(',')]
            
            # Store the template
            parameterized[section_name] = (params, config[key])
            keys_to_remove.append(key)
    
    # Remove parameterized sections from original config
    for key in keys_to_remove:
        del config[key]
    
    return parameterized


def _substitute_parameters_only(
    obj: Any, 
    param_bindings: Dict[str, str]
) -> Any:
    """
    Recursively substitute ONLY the parameter variables, leaving global
    interpolations intact for later resolution.
    
    Args:
        obj: The object to process (dict, list, str, or primitive)
        param_bindings: Mapping of parameter names to their values
        
    Returns:
        Object with parameters substituted but global vars preserved
    """
    if isinstance(obj, dict):
        return {
            k: _substitute_parameters_only(v, param_bindings) 
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [
            _substitute_parameters_only(item, param_bindings) 
            for item in obj
        ]
    elif isinstance(obj, str):
        # Only substitute parameters that are in param_bindings
        # Leave other interpolations like ${order} untouched
        result = obj
        for param_name, param_value in param_bindings.items():
            # Match ${param_name} specifically
            pattern = r'\$\{' + re.escape(param_name) + r'\}'
            result = re.sub(pattern, param_value, result)
        return result
    else:
        # Primitives pass through unchanged
        return obj


def _register_parameterized_resolvers(
    parameterized_sections: Dict[str, tuple]
) -> None:
    """
    Register OmegaConf resolvers for each parameterized section.
    These resolvers only substitute local parameters, leaving global
    variable interpolations for later resolution.
    """
    
    def create_resolver(params: List[str], template: Any):
        def resolver(*args):
            if len(args) != len(params):
                raise ValueError(
                    f"Expected {len(params)} arguments, got {len(args)}"
                )
            
            # Create parameter bindings
            param_bindings = {param: str(arg) for param, arg in zip(params, args)}
            
            # Substitute ONLY the parameters, leaving global vars as-is
            result = _substitute_parameters_only(template, param_bindings)
            
            return result
        
        return resolver
    
    for section_name, (params, template) in parameterized_sections.items():
        OmegaConf.register_new_resolver(
            section_name,
            create_resolver(params, template),
            replace=True
        )


def parse_config(config_file_path_or_dict: Path | ConfigDict | str,
                 cfg_class: SupportedConfigFormat = None):
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
            case Path() | str():
                # Ensure downstream the `Path` object is used consistently:
                config_file_path_or_dict = Path(config_file_path_or_dict)
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
            return _handle_dict_or_path(config_file_path_or_dict, dict, _parse_leaf_config_dict)
        case "attr" | "edict" | "ed":
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_easydict, _parse_config_easydict)
        case "omega" | "omegaconf" | "o":
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_omegaconfig, _parse_omegaconfig)
        case BaseModel():
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_pydantic, _parse_config_pydantic)
        case _:
            return _handle_dict_or_path(config_file_path_or_dict, _dict_to_kwarg_constructor, _parse_config_kwarg_constructor)


def flatten(config_dict: OmegaConfigDict | ConfigDict,
            parent_key: str = "",
            filter_: Iterable[str] | None = None,
            use_parent_key_for_filter: bool = False) -> Dict[str, Any]:
    """Flattens the config object to use dotlist keys, e.g.
    `{"a": {"b": [1, 2, 3]}}` will become `{"a.b": [1, 2, 3]}`

    Args:
        config_dict (OmegaConfigDict): parsed config dict
        parent_key (str, optional): parent key for recursion. Defaults to "".
        filter_ (Iterable[str] | None, optional): keys to filter from the input config. Defaults to None.
        use_parent_key_for_filter (bool, optional): skips last node in the keys. Defaults to False.

    Returns:
        Dict[str, Any]: flattened config dict
    """
    items = {}

    for key, value in config_dict.items():
        full_key = f"{parent_key}.{key}" if parent_key else key

        if isinstance(value, OmegaConfigDict) or isinstance(value, dict):
            items.update(flatten(value, full_key, filter_, use_parent_key_for_filter))
        else:
            if filter_ is None:
                items[full_key] = value
            else: 
                if key in filter_:
                    if use_parent_key_for_filter:
                        # Useful when we want to skip the last node for parsing `_doc_`s
                        full_key = parent_key
                    items[full_key] = value

    return items
