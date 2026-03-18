import sys
import argparse
import functools
from .parse import parse_config, SupportedConfigFormat, ConfigDict
from pathlib import Path
from typing import *
from rich.console import Console
from omegaconf import OmegaConf


def _load_and_override_config(config_path, config_format, named_overrides: dict, positional_overrides, verbose, console):
    """Load config from path, apply named and positional overrides, return in the target format."""
    if verbose:
        console.print(f"Fetching config: {config_path}")
    cfg = parse_config(Path(config_path), "o")
    if verbose:
        console.print(f"[green]Parsing of config at {config_path} succeeded[/green]")

    # Named overrides: arg name -> value (from argparse namespace or click kwargs)
    # Only applies when the key already exists in the config.
    for key, value in named_overrides.items():
        if value is None:
            continue
        existing = OmegaConf.select(cfg, key)
        if existing is not None:
            if verbose:
                console.print(f"Updating {key} with {value}")
            type_ = type(existing)
            if type_ is not type(None):
                value = type_(value)
            OmegaConf.update(cfg, key, value)

    # Positional key=value overrides (original confuk syntax)
    for arg in positional_overrides:
        key, value = arg.split("=")
        if verbose:
            console.print(f"Updating {key} with {value}")
        type_ = type(OmegaConf.select(cfg, key))
        if type_ is not type(None):
            value = type_(value)
        OmegaConf.update(cfg, key, value)

    cfg_primitive = OmegaConf.to_container(cfg, resolve=True)
    return parse_config(cfg_primitive, config_format)


def _reserve_config_arg(parser: argparse.ArgumentParser):
    """Inject -c/--config into parser. Raises ValueError if those flags are already in use."""
    for action in parser._actions:
        if '-c' in action.option_strings or '--config' in action.option_strings:
            raise ValueError(
                "'-c' and '--config' are reserved by confuk for config file loading. "
                "Please remove these from your ArgumentParser before passing it to confuk.main()."
            )
    parser.add_argument('-c', '--config', help="Config file path (confuk)", default=None)


def main(config: Path | str,
         config_format: SupportedConfigFormat,
         verbose=False,
         program_description="",
         parser: "argparse.ArgumentParser | None" = None):
    """
    Decorator that injects a parsed config object into a `main` function.

    When `parser` is provided (argparse drop-in mode):
    - `-c`/`--config` are added to the parser and reserved for config loading.
    - Any parsed argument whose name matches a key in the config will override that key.
    - The decorated function is called as `original_main(cfg, parsed_namespace)`.

    Without `parser` (original behaviour):
    - A minimal parser with `-c`/`--config`, `-v`/`--verbose`, and positional
      `key=value` overrides is created automatically.
    - The decorated function is called as `original_main(cfg)`.
    """

    console = Console()

    def main_decorator(original_main):

        @functools.wraps(original_main)
        def _main(*args):

            if parser is not None:
                # ---- argparse drop-in mode ----------------------------------------
                _reserve_config_arg(parser)
                cli_args = list(args) if len(args) > 0 else sys.argv[1:]
                parsed = parser.parse_args(cli_args)

                config_ = getattr(parsed, 'config', None) or config
                verbose_ = getattr(parsed, 'verbose', verbose)

                # All non-confuk args are candidates for config override
                reserved = {'config', 'verbose', 'overrides'}
                ns_dict = {k: v for k, v in vars(parsed).items() if k not in reserved}
                positional = getattr(parsed, 'overrides', ())

                cfg = _load_and_override_config(config_, config_format, ns_dict, positional, verbose_, console)
                return original_main(cfg, parsed)

            else:
                # ---- original behaviour -------------------------------------------
                inner_parser = argparse.ArgumentParser(description=program_description)
                inner_parser.add_argument('-c', "--config",
                                          help="Set to a different path to override the config path",
                                          default=None)
                inner_parser.add_argument('-v', "--verbose", help="Print verbose logs", default=verbose)
                inner_parser.add_argument('overrides',
                                          help="Key-value pairs formatted as `key=value` which override config properties",
                                          default=tuple(), nargs="*")
                cli_args = list(args) if len(args) > 0 else sys.argv[1:]
                parsed = inner_parser.parse_args(cli_args)

                config_ = parsed.config if parsed.config is not None else config

                cfg = _load_and_override_config(config_, config_format, {}, parsed.overrides, parsed.verbose, console)
                return original_main(cfg)

        return _main

    return main_decorator


def click_option(*args, cfg_path: str | None = None, **kwargs):
    """
    Drop-in replacement for ``@click.option`` that accepts an optional ``cfg_path`` argument.

    ``cfg_path`` is a dot-separated config key specifying which config property this
    option should override when used with ``@confuk.click_main``. Without ``cfg_path``,
    the option's own name is used as the config key (matching the default behaviour).

    Example::

        @confuk.click_main("config.yaml", MyConfig)
        @click.command()
        @confuk.click_option('--data', cfg_path="data.path")
        @confuk.click_option('--lr', type=float, cfg_path="training.lr")
        def my_main(cfg, data, lr):
            ...
    """
    try:
        import click
    except ImportError:
        raise ImportError(
            "click must be installed to use confuk.click_option(). "
            "Install it with: pip install click"
        )

    standard_decorator = click.option(*args, **kwargs)

    if cfg_path is None:
        return standard_decorator

    def decorator(func):
        result = standard_decorator(func)
        # click prepends each new option to __click_params__, so index 0 is the
        # most recently added — i.e. the one we just created above.
        result.__click_params__[0]._confuk_cfg_path = cfg_path
        return result

    return decorator


def click_main(config: Path | str,
               config_format: SupportedConfigFormat,
               verbose=False):
    """
    Decorator for click commands that injects a parsed config as the first argument.

    Usage::

        @confuk.click_main("config.yaml", MyConfig)
        @click.command()
        @confuk.click_option('--data', cfg_path="data.path")  # nested key override
        @click.option('--lr', type=float, default=None)       # top-level key override
        def my_main(cfg, data, lr):
            ...

    - ``-c``/``--config`` are added to the click command and reserved for config loading.
    - Options decorated with ``@confuk.click_option(..., cfg_path=...)`` override the
      specified dot-separated config key.
    - Options decorated with plain ``@click.option`` override the config key matching
      the option name, if such a key exists in the config.
    - The original callback is called as ``original_callback(cfg, **kwargs)`` where
      ``kwargs`` contains all click options (excluding ``config``).
    """
    try:
        import click
    except ImportError:
        raise ImportError(
            "click must be installed to use confuk.click_main(). "
            "Install it with: pip install click"
        )

    console = Console()

    def decorator(click_cmd):
        # Guard against reserved flag conflicts
        for param in click_cmd.params:
            if any(name in ('-c', '--config') for name in param.opts):
                raise ValueError(
                    "'-c' and '--config' are reserved by confuk for config file loading. "
                    "Please remove these from your click command before using confuk.click_main()."
                )

        # Build a mapping: click param name -> config dot-path (from cfg_path metadata)
        cfg_path_map: dict[str, str] = {
            param.name: param._confuk_cfg_path
            for param in click_cmd.params
            if hasattr(param, '_confuk_cfg_path')
        }

        # Inject the --config option at the front so it appears first in --help
        click_cmd.params.insert(0, click.Option(
            ('-c', '--config'),
            default=None,
            help="Config file path (confuk)",
        ))

        original_callback = click_cmd.callback

        @functools.wraps(original_callback)
        def new_callback(**kwargs):
            config_ = kwargs.pop('config', None) or config
            named_overrides = {
                cfg_path_map.get(k, k): v
                for k, v in kwargs.items()
                if v is not None
            }
            cfg = _load_and_override_config(config_, config_format, named_overrides, (), verbose, console)
            return original_callback(cfg, **kwargs)

        click_cmd.callback = new_callback
        return click_cmd

    return decorator
