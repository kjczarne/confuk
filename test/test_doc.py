import unittest
from confuk.parse import parse_config, flatten
from confuk.doc import extract_docs
from confuk.display import display_in_console, get_markdown_tree
from pathlib import Path


class TestDocGeneration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cfg_path = Path(__file__).parent / "test_interpolation.toml"
        cls.path = Path(__file__).parent / "test_doc.toml"
        cls.yaml_path = Path(__file__).parent / "test_doc.yaml"

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

    def test_multiline_doc_formatting(self):
        """Test that multiline documentation strings are properly indented in markdown output"""
        cfg = parse_config(self.yaml_path, "o")
        docs = extract_docs(cfg)
        
        # Generate the markdown tree
        markdown_output = get_markdown_tree(docs)
        
        # Check that multiline docs are present
        self.assertIn("some_node", markdown_output)
        self.assertIn("subnode", markdown_output)
        self.assertIn("subsubnode", markdown_output)
        
        # Check that code blocks are properly indented
        # Code blocks should be indented to align with list content
        self.assertIn("```bash", markdown_output)
        self.assertIn("ls -la", markdown_output)
        self.assertIn('echo "Nice!"', markdown_output)
        
        # Check that the structure maintains proper indentation levels
        lines = markdown_output.split('\n')
        
        # Find lines with code blocks and verify they're indented
        for i, line in enumerate(lines):
            if '```bash' in line:
                # Code block should be indented (at least 2 spaces)
                self.assertTrue(line.startswith('  '), 
                    f"Code block at line {i} should be indented: '{line}'")
            
            # Check that blockquotes are indented
            if line.strip().startswith('>'):
                self.assertTrue(line.startswith('  '),
                    f"Blockquote at line {i} should be indented: '{line}'")
        
        # Verify that list items within docs are indented
        self.assertIn("- As if you were", markdown_output)
        self.assertIn("- writing a basic", markdown_output)
        self.assertIn("- Markdown document", markdown_output)
        
        # Optional: Print for visual inspection during development
        # print("\n" + "="*80)
        # print("Generated Markdown:")
        # print("="*80)
        # print(markdown_output)
        # print("="*80)


if __name__ == "__main__":
    unittest.main()