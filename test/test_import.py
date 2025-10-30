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
        # Interpolation where the leaf nodes are updated after recursion into the imported configs is done:
        cls.path_lazy = Path(__file__).parent / "test_import_lazy.toml"
        # Importing in `post`, i.e. after the values from the directly parsed
        # config have already been parsed and interpolated:
        cls.path_post = Path(__file__).parent / "test_post_import.yaml"

    def test_import(self):
        for p in (self.path, self.path2):
            ed = parse_config(p, "attr")
            exp = {'something': {'value': 69, 'another_value': 2}, 'something_else': {'value': 3}}
            self.assertDictEqual(exp, ed)

    def test_import_lazy(self):
        ed = parse_config(self.path_lazy, "attr")
        self.assertEqual(ed.something_else.name_of_final_file, "test_import_lazy.toml")

    def test_post_import(self):
        ed = parse_config(self.path_post, "attr")
        self.assertEqual(ed.some_key, "lol")


if __name__ == "__main__":
    unittest.main()
