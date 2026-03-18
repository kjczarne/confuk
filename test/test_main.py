import unittest
from rich.console import Console
from confuk import main, click_main, click_option
from confuk.parse import ConfigDict
from pathlib import Path
from typing import *


@main(config=Path(__file__).parent / "test.toml", config_format="o", verbose=True)
def mock_main(cfg: ConfigDict, *args):
    console = Console()
    console.print(cfg)
    return cfg


class TestRead(unittest.TestCase):

    def test_main(self):
        r = mock_main()
        self.assertEqual(r.my.mother, 1)

    def test_main_overrides(self):
        r = mock_main("my.mother=2")
        self.assertEqual(r.my.mother, 2)

    def test_cli_config_override(self):
        r = mock_main(
            "--config",
            str(Path(__file__).parent / "test_imported.toml")
        )
        self.assertEqual(r.something_else.value, 3)


    def test_none_casting(self):
        r = mock_main(
            "--config",
            str(Path(__file__).parent / "test_none_casting.yaml"),
            "--",
            "some.something=lol"
        )
        self.assertEqual(r.some.something, "lol")
        self.assertIsInstance(r.some.something, str)

    def test_main_click_argument_parser_wrapper(self):
        import click
        from pydantic import BaseModel

        class Subconfig(BaseModel):
            y: int

        class Config(BaseModel):
            x: int
            sub: Subconfig

        p = str(Path(__file__).parent / "test_decorators.toml")
        @click_main(p, Config)
        @click.command()
        @click_option("--x", cfg_path="x", type=int)
        @click_option("--y", cfg_path="sub.y", type=int)
        def _main(cfg: Config, **kwargs) -> None:
            print(cfg.x)
            print(cfg.sub.y)
        
        try:
            _main()
        except SystemExit as e:
            print(f"Exit status: {e.args}")
            assert e.args[0] == 0


if __name__ == "__main__":
    unittest.main()
