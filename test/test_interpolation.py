from confuk import parse_config
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
                                  'path_to_this_file': str(self.path)}}
        self.assertDictEqual(exp, ed)
        # Comparing also string representations because in `OmegaConf`
        # dictionary equality comparison is overridden and you will not notice
        # that interpolation didn't happen after conversion back to a simple
        # dict unless you compare strings. The correct way of converting back
        # to a simple dict is `OmegaConf.to_container(config, resolve=True)`:
        self.assertEqual(str(ed), str(exp))


class TestParameterizedConfigs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).parent / "test_parameterized.yaml"
        cls.path_toml = cls.path.with_suffix(".toml")

    def test_single_parameter(self):
        """Test parameterized config with a single parameter."""
        cfg = parse_config(self.path, "omega")
        
        # Check that the parameterized section was invoked correctly
        self.assertEqual(
            cfg.variant_a[0].configurations[0].pdb,
            "data/experiment_1/s_awesometg1.pdb"
        )
        self.assertEqual(
            cfg.variant_b[0].configurations[0].pdb,
            "data/experiment_1/s_amazingtg1.pdb"
        )

    def test_multiple_parameters(self):
        """Test parameterized config with multiple parameters."""
        cfg = parse_config(self.path, "omega")
        
        # Check multiple parameter invocation
        self.assertEqual(
            cfg.custom_path_a.path,
            "data/exp1/s_awesometg1.pdb"
        )
        self.assertEqual(
            cfg.custom_path_b.path,
            "data/exp2/s_amazingtg2.pdb"
        )

    def test_parameter_resolution_in_nested_structures(self):
        """Test that parameters resolve correctly in deeply nested structures."""
        cfg = parse_config(self.path, "omega")
        
        # Check nested resolution
        variant = cfg.variant_a[0]
        self.assertEqual(variant.name, "Inactive target")
        self.assertEqual(variant.id, "h1")
        self.assertEqual(
            variant.configurations[0].data,
            "hotspot_data_1"
        )

    def test_parameter_count_mismatch(self):
        """Test that incorrect number of parameters raises an error."""
        # This would require a config that tries to invoke with wrong param count
        # The error should be raised during resolution
        pass  # Implement based on your error handling strategy

    def test_parameterized_with_global_interpolation(self):
        """Test that parameterized sections can access global config variables."""
        cfg = parse_config(self.path, "omega")
        
        # Both variants should use the same 'order' from global config
        self.assertTrue(cfg.variant_a[0].configurations[0].pdb.startswith("data/experiment_1/"))
        self.assertTrue(cfg.variant_b[0].configurations[0].pdb.startswith("data/experiment_1/"))

    def test_basic_toml_parametrized_interpolation(self):
        cfg = parse_config(self.path_toml, "omega")
        self.assertEqual(cfg.variant_a.some_data, "awesome_data")


if __name__ == "__main__":
    unittest.main()