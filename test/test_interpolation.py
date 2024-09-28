from confuk import parse_config
from pathlib import Path
import unittest


class TestImport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / "test_interpolation.toml"

    def test_import(self):
        ed = parse_config(self.path, "attr")
        exp = {'something': {'subsomething': {'lol': 'omg'}}, 'something_else': {'value_str': 'omg_lol'}}
        self.assertDictEqual(exp, ed)
        # Comparing also string representations because in `OmegaConf`
        # dictionary equality comparison is overridden and you will not notice
        # that interpolation didn't happen after conversion back to a simple
        # dict unless you compare strings. The correct way of converting back
        # to a simple dict is `OmegaConf.to_container(config, resolve=True)`:
        self.assertEqual(str(ed), str(exp))


if __name__ == "__main__":
    unittest.main()
