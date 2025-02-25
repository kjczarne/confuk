from confuk import dump_config
import unittest
from dataclasses import dataclass, field

@dataclass
class DummyCfg:
    a: int
    b: str


class TestDumpConfig(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DummyCfg(a=10, b="my momma").__dict__

    def test_dump_config(self):
        dump_config(self.config, "test/outputs/dump.json")
        dump_config(self.config, "test/outputs/dump.toml")
        dump_config(self.config, "test/outputs/dump.yaml")


if __name__ == "__main__":
    unittest.main()
