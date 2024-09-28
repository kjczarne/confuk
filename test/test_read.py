import unittest
from confuk import parse_config
from pathlib import Path
from typing import *
from easydict import EasyDict as edict
from omegaconf import DictConfig as OmegaConfigDict


class TestRead(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / "test.toml"
        cls.dct = {'my': {'mother': 1}, 'your': {'dad': {'father': 1}}}

    def _make_test_configs(self, args: Tuple[str]):
        configs = []
        for arg in args:
            cfg = parse_config(self.path, arg)
            configs.append(cfg)
        return configs

    def _make_test_type(self, cfg, type_: Type):
        self.assertIsInstance(cfg, type_)

    def _make_test_attr_dot_access(self, cfg):
        self.assertEqual(cfg.my.mother, 1)

    def _make_test_dict_equality(self, cfg):
        self.assertDictEqual(self.dct, dict(cfg))

    def _make_test_object_equality(self, cfg):
        self.assertEqual(self.dct, cfg)

    def test_read_dict(self):
        args = (None, "dict", "d")
        for cfg in self._make_test_configs(args):
            self._make_test_type(cfg, dict)
            self._make_test_dict_equality(cfg)

    def test_read_edict(self):
        args = ("attr", "ed", "edict")
        for cfg in self._make_test_configs(args):
            self._make_test_type(cfg, edict)
            self._make_test_dict_equality(cfg)
            self._make_test_attr_dot_access(cfg)

    def test_read_omegaconf(self):
        args = ("omegaconf", "o", "omega")
        for cfg in self._make_test_configs(args):
            self._make_test_type(cfg, OmegaConfigDict)
            self._make_test_attr_dot_access(cfg)
            self._make_test_object_equality(cfg)


if __name__ == '__main__':
    unittest.main()
