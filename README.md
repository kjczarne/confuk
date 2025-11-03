<img src="confuk-logo.drawio.png" width=150/>

# Confuk

This is yet another package for managing configuration files in Python projects.

It exposes one function that lets you provide a path to a TOML/YAML/JSON configuration file. It parses the config file into a dictionary by default. If a config class is provided when parsing, the class instance will be created using a dictionary of keyword arguments coming from the original TOML/YAML/JSON file.

In human words: I made this package so that I don't have to explicilty load, parse and return a class instance every single time I have something to do with a configuration file:

```python
from confuk import parse_config
from pathlib import Path
from somewhere import ConfigClass

cfg_dict = parse_config(Path("some.toml"))  # returns a dictionary
cfg_obj = parse_config(Path("some.toml"), ConfigClass)  # returns an instance of `ConfigClass`
```

> [!tip]
> `confuk` also supports a number of output configuration styles out-of-the-box, including `omegaconf`, Pydantic and `EasyDict`.

## Installation

```bash
pip install confuk
```

Or:

```bash
poetry add confuk
```

### Building from source

You can build the package using Poetry:

1. Clone this repo.
2. Run `poetry build`.
3. Grab the installable wheel from the `dist` folder and install it with `pip` or add the package as a local dependency of another project.

## Special features

### Config output formats

#### EasyDict

If you really hate referring to dictionary keys and you do not intend to create a custom configuration class for your config, you can parse the file to an `EasyDict`:

```python
cfg_edict = parse_config(Path("some.toml"), "attr")
```

Now, if the key `something` exists in the configuration file, you can simply refer to it using an attribute:

```python
cfg_edict.something
```

#### OmegaConf

[OmegaConf](https://omegaconf.readthedocs.io/) is one of the most complete configuration systems for Python applications. If you want to leverage its features while still working with `confuk` as a front-end, you can simply parse the configuration into an instance of `omegaconf.DictConfig` by doing the following:

```python
cfg = parse_config(Path("some.toml"), "omega")
```

#### Pydantic

If you're a fan of [Pydantic](https://docs.pydantic.dev/latest/) with custom config classes for automatic validation, just use any class that inherits from `BaseModel`:


```python
from confuk import parse_config
from pathlib import Path
from pydantic import BaseModel

class Metrics(BaseModel):
    psnr: float
    ssim: float


cfg_dict = parse_config(Path("some.toml"), Metrics)  # returns a dictionary
```

#### Supported input file formats

Currently we support the following input formats:

- Declarative config formats:

  - `.toml`
  - `.yaml`
  - `.json`

- Procedural config formats:

  - `.py` – a dictionary variable named `config` is required in the Python file to be loaded as a config instance.

#### Supported output formats

| Format      | `cfg_class` argument                               |
| ----------- | -------------------------------------------------- |
| `dict`      | `"d"` / `None`                                     |
| `EasyDict`  | `"ed"` / `"edict"` / `"attr"`                      |
| `OmegaConf` | `"o"` / `"omega"` / `"omegaconf"`                  |
| `pydantic`  | `BaseModel` class                                  |
| `custom`    | any class supporting `**kwargs` in the constructor |

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
    "${this_dir}/test_imported.toml",
]

[something]
value = 69
```

> [!note]
> Older versions of `confuk` used the `$this_dir` syntax instead. This will be supported going into the future but it won't work with variable interpolation (expect it to only work for the special interpolation markers such as `$this_dir` and `$cwd`).

This is equivalent to specifying a config like:

```toml
[something]
value = 69
another_value = 2

[something_else]
value = 3
```

Note that you can use several special interpolation markers to specify paths in the import section:

- `${this_dir}` -> points to a directory relative to the configuration file that contains the `import` section
- `${cwd}` -> points to the current working directory
- `${this_filename}` -> config filename (with extension)
- `${this_filename_stem}` -> filename without the extension (stem)
- `${this_dirname}` -> the name of the directory where the configuration file lives (not a path)
- `${this_filename_suffix}` -> suffix (without the dot) of the current configuration file

> [!warning]
> The preamble **will be removed** after it's processed. It's there only to control how `confuk` should process the loaded configuration files and it's dropped afterwards. Do not put any meaningful configuration into your preamble, except for `confuk`'s control elements.

#### Lazy interpolation

By default the interpolation markers like `${this_filename}` will interpolate the _current_ file name. So if for example you create `a.yaml` and it contains:

```yaml
pre:
  imports:
    - b.yaml
```

And `b.yaml` contains:

```yaml
filename: "${this_filename}"
```

Then `filename` will be **`b.yaml`**. This is expected as these markers are interpolated as-is in the file they were found in.

> [!important]
> **If you want to defer the interpolation of these markers to happen in the final config file, use `$[]` markers instead**.

So for example if you change `b.yaml` to contain:

```yaml
filename: "$[this_filename]"
```

Then `filename` will be `**a.yaml**` if you have called `parse_config` on the `a.yaml` file.

#### What about inheriting selected values?

Unsupported. And I do not plan to add support for cherrypicking values from other configs. It makes things way messier in my opinion, as it becomes way harder to reason about the flow of variables.

As far as accessing other values within imported config, read the next section – that is supported via OmegaConf.

#### What about variable interpolation?

This is supported with the syntax that [OmegaConf](https://omegaconf.readthedocs.io/) uses, e.g. `path = "${some.root.path}/file.txt"` will pick up the `path` variable from `some.root` config section. The interpolation markers that I mentioned in the `Imports` section should also work anywhere else within the config, so you can use your `${this_filename_stem}` to refer to config names within the config itself. One use-case is when you want to have subdirectories in a `results` directory, where you would silo away the results from different configs:

```toml
results_dir = "results/${this_filename_stem}"
```

Assumming that you have 3 configs for your experiments: `ex1`, `ex2` and `ex3`, you could instead put `results_dir` in a parent config to all those:

```toml
# to_import.toml:
results_dir = "results/${this_filename_stem}"

# ex1
[pre]
imports = ["${this_dir}/to_import.toml"]
a_variable_that_diverges_across_configs = 69

# ex2
[pre]
imports = ["${this_dir}/to_import.toml"]
a_variable_that_diverges_across_configs = 420

# ex3
[pre]
imports = ["${this_dir}/to_import.toml"]
a_variable_that_diverges_across_configs = 42
```

> [!note]
> We are using `omegaconf` for all other interpolation tasks under the hood since they already have a great parser for this and there's no use duplicating work.

#### What about deeply nested configs?

If you like the deeply nested folder-file structure for your configs then [Hydra](https://hydra.cc/) might be more for you. I've used it before and it's very good but I personally find the design choice of creating directory structures for configs quite tedious.

`confuk` strives to be flatter: you import another config file in the preamble section and you have a choice of what to override. This makes it more comfortable to use when you have one `default.toml` config file for something and then create a bunch of configurations overriding certain values. This is useful for experiments in the AI/ML space, where I'm spending most of my time now.

You are of course free to structure your files as you please but don't expect a feature similar to Hydra's `defaults` in `confuk` – I do indeed use Hydra for applications which require such a system!

### Lambda-configs (templates)

What if you want to reuse a portion of the config but parametrize on some variable? As an example imagine you want to have multiple variants in the config and want to reuse a YAML snippet in multiple places but with some variable changed:

```yaml
experiment: "exp_1"

target_variants(crazy):
  - name: "Inactive target"
    id: "h1"
    configurations:
      - id: "HT"
        pdb: "data/${experiment}/s_${crazy}tg1.pdb"

variant_a: "${target_variants:awesome}"
variant_b: "${target_variants:amazing}"
```

In `confuk` you can simply specify a parameter (`crazy` in the example above). Underneath this will automatically create an OmegaConf resolver that accepts the right number of inputs. So if you want to "call" this pseudo-function with `awesome` you would use `${target_variants:awesome}`.

> [!note]
> This is available starting with version `0.11.0` of `confuk`.

### Post-loading imports

Sometimes you might want to use an imported config which has some particular key interpolated from the file that actually imports it. For example assume `test_post_imported.yaml` looks like this:

```yaml
some_key: "${deferred}"
```

Then you can use it like so:

```yaml
deferred: "lol"

post:
  imports:
    - "${this_dir}/test_post_imported.yaml"

```

When loaded in the `post` section, the `${deferred}` key will be interpolated in the imported config _after_ the config which is the leaf node in the import graph. This way `some_key` will have the value of `"lol"` in the example.

### Command-line overrides

One of the most fantastic features I've found when using [Hydra](https://hydra.cc/) was the ability to override values from the config file on the command line. This is convenient when you want to quickly test some changes to your configuration without going through the trouble of creating a new config file.

So I concluded it would be fun to implement it in `confuk` in a similar fashion. Here's how it works:

```python
import confuk


@confuk.main(config=Path(__file__).parent / "test.toml", config_format="o", verbose=False)
def main(cfg, *args):
    console = Console()
    console.print(cfg)
    return cfg
```

This decorator behaves similarly to `@hydra.main` decorator and it creates a minimal argument parser for your application entrypoint under the hood.

Now, when running the app, you can specify any value overrides on the command line. For example if your config looks like this:

```toml
[my]
mother = 1

[your.dad]
father = 1
```

And you run your CLI app with the argument `your.dad.father=3`, you will override the pertinent value from `1` to `3`.

> [!tip]
> The underlying argument parser also contains a `--config` option. You can use it to switch to a different config path on the command line, without a need to rely on the default one that has been set in the decorator.

### Dumping configs

This is mostly for debugging purposes.

Sometimes, when you use a lot of imports it might be hard to figure out what is the final config form after all the imports have been resolved. Starting from version `0.8.0` you can now dump your configs to JSON, YAML, TOML, Pickle and JSONPickle and the routing is done using file extensions:

- `*.json` – dump to JSON
- `*.yaml` – dump to YAML
- `*.toml` – dump to TOML
- `*.jsonp` – dump to JSONPickle
- `*.pkl` – dump to Pickle

To perform the dumping just use:

```python
from confuk import dump_config

dump_config(cfg, "some_cfg.json")
```

> [!warning]
> Not all types in your config object might be serializable, especially if you're using custom classes. When loading a config using `omegaconf` adapter, we're ensuring that the output is serialized properly, with other config backends it might not be so pretty at the moment. If you're running into trouble my suggestion is to dump to a Pickle and use something like [objexplore](https://github.com/kylepollina/objexplore) to load the Pickle back again and explore the contents of the constructed config.

### Config file documentation

When designing a config file, you will often want to also document what each property means. Sadly enough, there aren't that many packages which handle config documentation very well. This is partially due to limitations of file formats used for configuration. For example YAML and TOML specifications do not cover parsing comments, meanwhile a lot of folks out there use comments to document parts of their config files:

```yaml
apple:
  # Color of the apple
  color: red
  # Size of the apple
  size: medium
```

We thought of implementing parsing for these but seriously, who would have time to build a reliable new parser for YAML or TOML which also processes comments correctly? Instead, it was much simpler to go with a separate documentation file. For the example above, you would create another file, e.g. `config.doc.yaml`:

```yaml
apple:
  _doc_: properties of an apple
  color:
    _doc_: Color of the apple
  size:
    _doc_: Size of the apple
```

Then you can simply run:

```bash
confuk doc ./config.doc.yaml
```

This will display the documentation in the console, paged for your pleasure of reading. You have currently the following alternative options to display the contents of the documentation:

- `confuk doc ./config.doc.yaml -f test.html` – as an HTML file (append `-o` to open it in the web browser right away)
- `confuk doc ./config.doc.yaml -t` – in a tree view (might be more helpful for figuring out complex hierarchies)

### Parsing configs on the command line

Because sometimes you might want to display the cumulative config files after the imports and interpolations have been resolved, we added as an alternative to dumping to a file a command-line based print of the collected config:

```bash
confuk parse <path-to-config>
```

### Logging

For more complex applications it's probably more useful to set up your own logging facilities the way you need them. For basic applications, you might use the `get_console_and_logger` function which accepts a simple logging config (which can be a part of your main config file):

```yaml
logging:
  level: info
  logfile: null
```

The function returns a `rich.console.Console` and a `logging.Logger` instance which are tied together and can be used througout your application.
