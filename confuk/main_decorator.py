import sys
import argparse
import functools
from .parse import parse_config, SupportedConfigFormat, ConfigDict
from pathlib import Path
from typing import *
from rich.console import Console
from omegaconf import OmegaConf


def main(config: Path | str,
         config_format: SupportedConfigFormat,
         verbose=False,
         program_description=""):

    console = Console()

    def main_decorator(original_main):

        @functools.wraps(original_main)
        def _main(*args):
            parser = argparse.ArgumentParser(description=program_description)
            parser.add_argument('-c', "--config", help="Set to a different path to override the config path",
                                default=None)
            parser.add_argument('-v', "--verbose", help="Print verbose logs", default=verbose)
            parser.add_argument('overrides',
                                help="Key-value pairs formatted as `key=value` which override config properties",
                                default=tuple(), nargs="*")
            # Handle argument list:
            if len(args) > 0:
                args = parser.parse_args(args)
            else:
                args = parser.parse_args(sys.argv[1:])

            # Handle the config override from the command line interface:
            if args.config is not None:
                # Overridden:
                config_ = args.config
            else:
                # From outer scope:
                config_ = config

            # Parse the selected config file:
            if args.verbose:
                console.print(f"Fetching config: {config_}")
            cfg_omegaconf = parse_config(Path(config_), "o")
            if args.verbose:
                console.print(f"[green]Parsing of config at {config_} succeeded[/green]")

            # Handle overrides:
            for arg in args.overrides:
                key, value = arg.split("=")
                if args.verbose:
                    console.print(f"Updating {key} with {value}")
                # Fetch the type of the value if it already exists and cast the type:
                type_ = type(OmegaConf.select(cfg_omegaconf, key))
                # ... but do it only if the type is actually known at this stage:
                if type_ is not type(None):
                    value = type_(value)
                # Finally update the original config instance:
                OmegaConf.update(cfg_omegaconf, key, value)

            # Conver `omegaconf` instance to a primitive dict:
            cfg_in_a_primitive_format = OmegaConf.to_container(cfg_omegaconf, resolve=True)

            # Then use that dict and create the desired output config format:
            cfg_in_the_output_format = parse_config(cfg_in_a_primitive_format, config_format)
            return original_main(cfg_in_the_output_format)
        return _main

    return main_decorator
