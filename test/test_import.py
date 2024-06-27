from confuk import parse_config
from pathlib import Path
import unittest


class TestImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / "test_import.toml"

    def test_import(self):
        ed = parse_config(self.path, "attr")
        exp = {'something': {'value': 69, 'another_value': 2}, 'something_else': {'value': 3}}
        self.assertDictEqual(exp, ed)


if __name__ == "__main__":
    unittest.main()
