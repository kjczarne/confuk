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

```bash
pip install confuk
```

Or:

```bash
poetry add confuk
```

### Building from source

Currently you can build the package using Poetry:

1. Clone this repo.
2. Run `poetry build`.
3. Grab the installable wheel from the `dist` folder and install it with `pip` or add the package as a local dependency of another project.

Once I get some time to take care of it I will add the package to PyPI so that it's installable via a simple `pip install confuk` command.

## Special features

### EasyDict parsing

If you really hate referring to dictionary keys and you do not intend to create a custom configuration class for your config, you can parse the file to an `EasyDict`:

```python
cfg_edict = parse_config(Path("some.toml"), "attr")  # returns a dictionary
```

Now, if the key `something` exists in the configuration file, you can simply refer to it using an attribute:

```python
cfg_edict.something
```

### Imports

Because keeping hundreds of config files can become tedious, especially when there is shared values between them, you might want to consider using the `imports` functionality.

Say you have a TOML file from which you want to inherit values:

```toml
[something]
value = 1
another_value = 2

[something_else]
value = 3
```

You can "import" it using a preamble:

```toml
[pre]
imports = [
    "$this_dir/test_imported.toml",
]

[something]
value = 69
```

This is equivalent to specifying a config like:

```toml
[something]
value = 69
another_value = 2

[something_else]
value = 3
```

Note that you can use two special interpolation markers to specify paths in the import section:
- `$this_dir` -> points to a directory relative to the TOML file that contains the `import` section
- `$cwd` -> points to the current working directory

> [!warning]
> The preamble **will be removed** after it's processed. It's there only to control how `confuk` should process the loaded configuration files and it's dropped afterwards. Do not put any meaningful configuration into your preamble, except for `confuk`'s control elements.

#### What about inheriting selected values?

Unsupported. And I do not plan to add support for cherrypicking values from other configs. It makes things way messier in my opinion, as it becomes way harder to reason about the flow of variables.
