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
            parser.add_argument('-v', "--verbose", help="Print verbose logs", default=verbose)
            parser.add_argument('overrides',
                                help="Key-value pairs formatted as `key=value` which override config properties",
                                default=tuple(), nargs="*")
            if len(args) > 0:
                args = parser.parse_args(args)
            else:
                args = parser.parse_args(sys.argv[1:])

            if args.verbose:
                console.print(f"Fetching config: {config}")
            cfg_omegaconf = parse_config(config, "o")
            if args.verbose:
                console.print(f"[green]Parsing of config at {config} succeeded[/green]")

            for arg in args.overrides:
                key, value = arg.split("=")
                if args.verbose:
                    console.print(f"Updating {key} with {value}")
                # fetch the type of the value if it already exists and cast the type:
                value = type(OmegaConf.select(cfg_omegaconf, key))(value)
                OmegaConf.update(cfg_omegaconf, key, value)
                
            cfg_in_a_primitive_format = OmegaConf.to_container(cfg_omegaconf, resolve=True)
            cfg_in_the_output_format = parse_config(cfg_in_a_primitive_format, config_format)
            return original_main(cfg_in_the_output_format)
        return _main

    return main_decorator
