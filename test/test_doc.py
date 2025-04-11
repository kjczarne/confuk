import unittest
from confuk.parse import parse_config, flatten
from confuk.doc import extract_docs
from confuk.display import display_in_console
from pathlib import Path


class TestDocGeneration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cfg_path = Path(__file__).parent / "test_interpolation.toml"
        cls.path = Path(__file__).parent / "test_doc.toml"

    def test_flatten(self):
        cfg = parse_config(self.cfg_path, "o")
        flattened = flatten(cfg)
        for k in ['something.subsomething.lol', 'something_else.value_str', 'something_else.path_to_this_file']:
            self.assertIn(k, flattened.keys())
        # print(flattened)

    def test_doc_extraction(self):
        cfg = parse_config(self.path, "o")
        docs = extract_docs(cfg)
        dct = {'': 'lol', 'something': 'lol', 'something.subsomething': 'Now this is something!', 'something.subsomething_else': 'Now this is something else!'}
        self.assertDictEqual(dct, docs)
        # display_in_console(docs, tree_view=True)


if __name__ == "__main__":
    unittest.main()
