from confuk import parse_config
from confuk.parse import _apply_regex_repl_if_present
from pathlib import Path
import unittest


class TestImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / "test_interpolation.toml"

    def test_import(self):
        ed = parse_config(self.path, "attr")
        exp = {'something': {'subsomething': {'lol': 'omg'}},
               'something_else': {'value_str': 'omg_lol',
                                  'path_to_this_file': str(self.path),
                                  'with_substitution': str(self.path).replace("interpolation", "transplantation"),
                                  'with_substitution_lazy': str(self.path).replace("interpolation", "transplantation") + "_v"}}
        self.assertDictEqual(exp, ed)
        # Comparing also string representations because in `OmegaConf`
        # dictionary equality comparison is overridden and you will not notice
        # that interpolation didn't happen after conversion back to a simple
        # dict unless you compare strings. The correct way of converting back
        # to a simple dict is `OmegaConf.to_container(config, resolve=True)`:
        # print(ed)
        self.assertEqual(str(ed), str(exp))

    def test_regex_substitution(self):
        markers = ["$[this_filename_stem:::s/_ft//]", "$[this_filename_stem:::s/asdf/1234/]", "$[this_filename_stem:::s/asdf/1234/]_v"]
        exps = ["asdf", "1234_ft", "1234_ft_v"]
        for marker, exp in zip(markers, exps):
            actual = _apply_regex_repl_if_present(marker, "asdf_ft")
            self.assertEqual(actual, exp)


if __name__ == "__main__":
    unittest.main()
