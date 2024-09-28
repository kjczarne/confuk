from confuk import parse_config
from pathlib import Path
import unittest


class TestImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Interpolation with the old `$this` syntax:
        cls.path = Path(__file__).parent / "test_import.toml"
        # Interpolation with the new `${this}` syntax:
        cls.path2 = Path(__file__).parent / "test_import2.toml"

    def test_import(self):
        for p in (self.path, self.path2):
            ed = parse_config(p, "attr")
            exp = {'something': {'value': 69, 'another_value': 2}, 'something_else': {'value': 3}}
            self.assertDictEqual(exp, ed)


if __name__ == "__main__":
    unittest.main()
