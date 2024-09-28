import unittest
from rich.console import Console
from confuk import main
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


if __name__ == "__main__":
    unittest.main()
