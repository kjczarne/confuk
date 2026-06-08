import unittest
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, Union

from omegaconf import DictConfig, ListConfig, OmegaConf

from confuk.from_config import (
    ConfigMixin,
    _unwrap_optional,
    config_dataclass,
    from_config,
)


# --------------------------------------------------------------------------- #
# Shared fixtures
# --------------------------------------------------------------------------- #
@dataclass
class Inner:
    value: int


@dataclass
class Item:
    val: int


# --------------------------------------------------------------------------- #
# from_config
# --------------------------------------------------------------------------- #
class TestFromConfig(unittest.TestCase):

    def test_all_fields_from_dict(self):
        @dataclass
        class Cfg:
            x: int
            y: str

        result = from_config(Cfg, {"x": 1, "y": "hello"})
        self.assertEqual(result.x, 1)
        self.assertEqual(result.y, "hello")

    def test_all_fields_from_dictconfig(self):
        @dataclass
        class Cfg:
            x: int
            y: str

        cfg = OmegaConf.create({"x": 1, "y": "hello"})
        result = from_config(Cfg, cfg)
        self.assertEqual(result.x, 1)
        self.assertEqual(result.y, "hello")

    def test_absent_field_uses_default(self):
        @dataclass
        class Cfg:
            x: int
            y: str = "default"

        result = from_config(Cfg, {"x": 1})
        self.assertEqual(result.y, "default")

    def test_absent_field_uses_default_factory(self):
        @dataclass
        class Cfg:
            x: int
            items: list = field(default_factory=list)

        result = from_config(Cfg, {"x": 1})
        self.assertEqual(result.items, [])

    def test_required_field_absent_raises_type_error(self):
        @dataclass
        class Cfg:
            x: int
            y: str  # no default

        with self.assertRaises(TypeError):
            from_config(Cfg, {"x": 1})

    def test_non_dataclass_raises_type_error(self):
        class NotDC:
            pass

        with self.assertRaises(TypeError):
            from_config(NotDC, {})

    def test_missing_marker_defers_to_default(self):
        """'???' in config should be treated as absent, deferring to the field default."""
        @dataclass
        class Cfg:
            x: int
            y: str = "fallback"

        cfg = OmegaConf.create({"x": 1, "y": "???"})
        result = from_config(Cfg, cfg)
        self.assertEqual(result.y, "fallback")

    def test_missing_marker_on_required_field_raises_type_error(self):
        """'???' on a required field (no default) should still raise TypeError."""
        @dataclass
        class Cfg:
            x: int
            y: str  # no default

        cfg = OmegaConf.create({"x": 1, "y": "???"})
        with self.assertRaises(TypeError):
            from_config(Cfg, cfg)

    def test_init_false_field_is_skipped(self):
        """Fields with init=False must not be passed to __init__, even if in config."""
        @dataclass
        class Cfg:
            x: int
            y: str = field(init=False, default="computed")

        result = from_config(Cfg, {"x": 1, "y": "should_be_ignored"})
        self.assertEqual(result.y, "computed")

    def test_extra_keys_ignored_by_default(self):
        @dataclass
        class Cfg:
            x: int

        result = from_config(Cfg, {"x": 1, "extra": "oops"})
        self.assertEqual(result.x, 1)

    def test_strict_raises_on_extra_keys(self):
        @dataclass
        class Cfg:
            x: int

        with self.assertRaises(ValueError):
            from_config(Cfg, {"x": 1, "extra": "oops"}, strict=True)

    def test_strict_passes_with_no_extra_keys(self):
        @dataclass
        class Cfg:
            x: int

        result = from_config(Cfg, {"x": 1}, strict=True)
        self.assertEqual(result.x, 1)

    def test_interpolation_resolved(self):
        @dataclass
        class Cfg:
            x: int
            y: int

        cfg = OmegaConf.create({"x": 10, "y": "${x}"})
        result = from_config(Cfg, cfg)
        self.assertEqual(result.y, 10)

    def test_empty_config_all_defaults(self):
        @dataclass
        class Cfg:
            x: int = 5
            y: str = "hi"

        result = from_config(Cfg, {})
        self.assertEqual(result.x, 5)
        self.assertEqual(result.y, "hi")

    def test_empty_config_no_fields(self):
        @dataclass
        class Cfg:
            pass

        result = from_config(Cfg, {})
        self.assertIsInstance(result, Cfg)


# --------------------------------------------------------------------------- #
# Nested dataclass recursion
# --------------------------------------------------------------------------- #
class TestNestedRecursion(unittest.TestCase):

    def test_nested_dataclass(self):
        @dataclass
        class Outer:
            name: str
            inner: Inner

        cfg = OmegaConf.create({"name": "test", "inner": {"value": 42}})
        result = from_config(Outer, cfg)
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)

    def test_optional_nested_dataclass_present(self):
        @dataclass
        class Outer:
            name: str
            inner: Optional[Inner] = None

        cfg = OmegaConf.create({"name": "test", "inner": {"value": 99}})
        result = from_config(Outer, cfg)
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 99)

    def test_optional_nested_dataclass_absent_uses_none(self):
        @dataclass
        class Outer:
            name: str
            inner: Optional[Inner] = None

        result = from_config(Outer, {"name": "test"})
        self.assertIsNone(result.inner)

    def test_list_of_dataclasses(self):
        @dataclass
        class Container:
            items: List[Item]

        cfg = OmegaConf.create({"items": [{"val": 1}, {"val": 2}]})
        result = from_config(Container, cfg)
        self.assertEqual(len(result.items), 2)
        self.assertIsInstance(result.items[0], Item)
        self.assertEqual(result.items[0].val, 1)
        self.assertEqual(result.items[1].val, 2)

    def test_tuple_of_dataclasses(self):
        @dataclass
        class Container:
            items: Tuple[Item, ...]

        cfg = OmegaConf.create({"items": [{"val": 3}, {"val": 4}]})
        result = from_config(Container, cfg)
        self.assertIsInstance(result.items, tuple)
        self.assertEqual(result.items[0].val, 3)
        self.assertEqual(result.items[1].val, 4)

    def test_deeply_nested_dataclass(self):
        @dataclass
        class Deep:
            z: float

        @dataclass
        class Mid:
            deep: Deep
            label: str

        @dataclass
        class Top:
            mid: Mid

        cfg = OmegaConf.create({"mid": {"deep": {"z": 3.14}, "label": "mid"}})
        result = from_config(Top, cfg)
        self.assertIsInstance(result.mid, Mid)
        self.assertIsInstance(result.mid.deep, Deep)
        self.assertAlmostEqual(result.mid.deep.z, 3.14)


# --------------------------------------------------------------------------- #
# Raw OmegaConf container fields
# --------------------------------------------------------------------------- #
class TestRawContainerFields(unittest.TestCase):

    def test_dictconfig_typed_field_returns_dictconfig(self):
        @dataclass
        class Cfg:
            extra: DictConfig

        cfg = OmegaConf.create({"extra": {"a": 1, "b": 2}})
        result = from_config(Cfg, cfg)
        self.assertIsInstance(result.extra, DictConfig)

    def test_listconfig_typed_field_returns_listconfig(self):
        @dataclass
        class Cfg:
            items: ListConfig

        cfg = OmegaConf.create({"items": [1, 2, 3]})
        result = from_config(Cfg, cfg)
        self.assertIsInstance(result.items, ListConfig)

    def test_any_typed_dict_field_converts_to_native(self):
        """An untyped (Any) dict value should be converted to native Python."""
        @dataclass
        class Cfg:
            data: Any

        cfg = OmegaConf.create({"data": {"nested": {"deep": 1}}})
        result = from_config(Cfg, cfg)
        self.assertIsInstance(result.data, dict)
        self.assertEqual(result.data["nested"]["deep"], 1)

    def test_any_typed_list_field_converts_to_native(self):
        @dataclass
        class Cfg:
            data: Any

        cfg = OmegaConf.create({"data": [1, 2, 3]})
        result = from_config(Cfg, cfg)
        self.assertIsInstance(result.data, list)
        self.assertEqual(result.data, [1, 2, 3])


# --------------------------------------------------------------------------- #
# ConfigMixin
# --------------------------------------------------------------------------- #
class TestConfigMixin(unittest.TestCase):

    def test_classmethod_basic(self):
        @dataclass
        class TrainConfig(ConfigMixin):
            lr: float = 1e-3
            epochs: int = 100

        result = TrainConfig.from_config({"lr": 5e-4})
        self.assertAlmostEqual(result.lr, 5e-4)
        self.assertEqual(result.epochs, 100)

    def test_classmethod_strict_raises_on_extra(self):
        @dataclass
        class TrainConfig(ConfigMixin):
            lr: float = 1e-3

        with self.assertRaises(ValueError):
            TrainConfig.from_config({"lr": 0.01, "unknown": True}, strict=True)

    def test_classmethod_strict_passes_without_extra(self):
        @dataclass
        class TrainConfig(ConfigMixin):
            lr: float = 1e-3

        result = TrainConfig.from_config({"lr": 0.01}, strict=True)
        self.assertAlmostEqual(result.lr, 0.01)

    def test_classmethod_uses_dictconfig(self):
        @dataclass
        class Cfg(ConfigMixin):
            x: int

        cfg = OmegaConf.create({"x": 7})
        result = Cfg.from_config(cfg)
        self.assertEqual(result.x, 7)


# --------------------------------------------------------------------------- #
# config_dataclass decorator
# --------------------------------------------------------------------------- #
class TestConfigDataclass(unittest.TestCase):

    def test_injects_from_config(self):
        @config_dataclass
        @dataclass
        class DecoratedCfg:
            lr: float = 1e-3

        self.assertTrue(hasattr(DecoratedCfg, "from_config"))
        result = DecoratedCfg.from_config({"lr": 0.01})
        self.assertAlmostEqual(result.lr, 0.01)

    def test_defers_to_default(self):
        @config_dataclass
        @dataclass
        class DecoratedCfg:
            lr: float = 1e-3

        result = DecoratedCfg.from_config({})
        self.assertAlmostEqual(result.lr, 1e-3)

    def test_strict_mode_via_decorator(self):
        @config_dataclass
        @dataclass
        class DecoratedCfg:
            lr: float = 1e-3

        with self.assertRaises(ValueError):
            DecoratedCfg.from_config({"lr": 0.01, "extra": True}, strict=True)

    def test_raises_on_non_dataclass(self):
        class NotDC:
            lr: float = 1e-3

        with self.assertRaises(TypeError):
            config_dataclass(NotDC)


# --------------------------------------------------------------------------- #
# _unwrap_optional
# --------------------------------------------------------------------------- #
class TestUnwrapOptional(unittest.TestCase):

    def test_optional_int(self):
        self.assertIs(_unwrap_optional(Optional[int]), int)

    def test_union_with_none(self):
        self.assertIs(_unwrap_optional(Union[str, None]), str)

    def test_genuine_union_unchanged(self):
        tp = Union[int, str]
        self.assertEqual(_unwrap_optional(tp), tp)

    def test_plain_type_unchanged(self):
        self.assertIs(_unwrap_optional(int), int)

    def test_optional_dataclass(self):
        self.assertIs(_unwrap_optional(Optional[Inner]), Inner)


if __name__ == "__main__":
    unittest.main()
