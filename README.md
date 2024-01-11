# Confuk

This is yet another package for managing configuration files in Python projects.

At the moment all it does is it exposes a consistent API that lets you provide a path to a TOML configuration file. It parses the config file into a dictionary by default. If a config class is provided when parsing, the class instance will be created using a dictionary of keyword arguments coming from the original TOML file.

In human words: I made this package so that I don't have to explicilty load, parse and return a class instance every single time I have something to do with a TOML file:

```python
from confuk import parse_config
from pathlib import Path
from somewhere import ConfigClass

cfg_dict = parse_config(Path("some.toml"))  # returns a dictionary
cfg_obj = parse_config(Path("some.toml"), ConfigClass)  # returns an instance of `ConfigClass`
```

## Installation

Currently you can build the package using Poetry:

1. Clone this repo.
2. Run `poetry build`.
3. Grab the installable wheel from the `dist` folder and install it with `pip` or add the package as a local dependency of another project.

Once I get some time to take care of it I will add the package to PyPI so that it's installable via a simple `pip install confuk` command.
