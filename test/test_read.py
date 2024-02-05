import unittest
from confuk import parse_config
from pathlib import Path


class TestRead(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / "test.toml"
        cls.dct = {'my': {'mother': 1}, 'your': {'dad': {'father': 1}}}

    def test_read_edict(self):
        ed = parse_config(self.path, "attr")
        self.assertDictEqual(self.dct, ed)
        self.assertEqual(ed.my.mother, 1)


if __name__ == '__main__':
    unittest.main()
