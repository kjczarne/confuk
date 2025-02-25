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
        cls.config = DummyCfg(a=10, b="my momma")
        cls.config_dict = cls.config.__dict__

    def test_dump_config(self):
        dump_config(self.config_dict, "test/outputs/dump.json")
        dump_config(self.config_dict, "test/outputs/dump.toml")
        dump_config(self.config_dict, "test/outputs/dump.yaml")
        dump_config(self.config, "test/outputs/dump.jsonp")
        dump_config(self.config, "test/outputs/dump.pkl")


if __name__ == "__main__":
    unittest.main()
