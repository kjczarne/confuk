from confuk import dump_config
import unittest
from dataclasses import dataclass, field
from omegaconf import DictConfig

@dataclass
class DummyCfg:
    a: int
    b: str


class TestDumpConfig(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = DummyCfg(a=10, b="my momma")
        cls.config_dict = cls.config.__dict__
        cls.omegaconf = DictConfig(cls.config_dict)

    def test_dump_config(self):
        dump_config(self.config_dict, "test/outputs/dump.json")
        dump_config(self.config_dict, "test/outputs/dump.toml")
        dump_config(self.config_dict, "test/outputs/dump.yaml")
        dump_config(self.config, "test/outputs/dump.jsonp")
        dump_config(self.config, "test/outputs/dump.pkl")
        dump_config(self.omegaconf, "test/outputs/dump_omegaconf.toml")
        dump_config(self.omegaconf, "test/outputs/dump_omegaconf.yaml")
        dump_config(self.omegaconf, "test/outputs/dump_omegaconf.json")


if __name__ == "__main__":
    unittest.main()
