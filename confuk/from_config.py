"""Populate dataclasses from OmegaConf configs, deferring to field defaults.

The single rule: for every ``init`` field of the dataclass, take the value from
the config *if and only if* it is present and not ``MISSING``; otherwise leave it
out of the constructor call so the dataclass's own default (or ``default_factory``)
applies. Required fields with no default that are absent from the config raise the
normal ``TypeError`` from ``__init__`` -- the missing-key error you actually want.

Intended to live in ``confuk`` so you never hand-write a constructor full of
``OmegaConf.select(...)`` calls again::

    from confuk import ConfigMixin   # or: from confuk import from_config

    @dataclass
    class TrainConfig(ConfigMixin):
        lr: float = 1e-3
        epochs: int = 100

    TrainConfig.from_config(cfg)
"""

from __future__ import annotations

import typing
from dataclasses import fields, is_dataclass
from typing import Any, Type, TypeVar, get_args, get_origin

from omegaconf import DictConfig, ListConfig, OmegaConf

__all__ = ["from_config", "ConfigMixin", "config_dataclass"]

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Type-hint helpers
# --------------------------------------------------------------------------- #
def _resolve_hints(cls: type) -> dict[str, Any]:
    """Return resolved annotations for ``cls``.

    Tolerates PEP 563 (``from __future__ import annotations``) string annotations
    and unresolvable forward references. On failure, falls back to the raw
    ``__annotations__`` (which may contain strings); in that degraded case scalar
    and plain-container fields still work, but nested-dataclass recursion is
    skipped because the type is only known as a string.
    """
    try:
        return typing.get_type_hints(cls)
    except Exception:
        hints: dict[str, Any] = {}
        for klass in reversed(getattr(cls, "__mro__", [cls])):
            hints.update(getattr(klass, "__annotations__", {}))
        return hints


def _unwrap_optional(tp: Any) -> Any:
    """``Optional[X]`` / ``Union[X, None]`` -> ``X``; otherwise unchanged.

    Only unwraps when exactly one non-``None`` member remains, so genuine unions
    like ``Union[int, str]`` are left intact.
    """
    if get_origin(tp) is typing.Union:
        non_none = [a for a in get_args(tp) if a is not type(None)]  # noqa: E721
        if len(non_none) == 1:
            return non_none[0]
    return tp


# --------------------------------------------------------------------------- #
# Value conversion
# --------------------------------------------------------------------------- #
def _convert(value: Any, tp: Any) -> Any:
    """Convert one config value according to the declared field type ``tp``."""
    # The field explicitly asked for a raw OmegaConf container: don't touch it.
    if tp in (DictConfig, ListConfig):
        return value

    tp = _unwrap_optional(tp)

    # Nested dataclass -> recurse.
    if is_dataclass(tp) and isinstance(value, DictConfig):
        return from_config(tp, value)

    # Sequence of dataclasses, e.g. list[Layer] / tuple[Layer, ...] -> recurse per item.
    origin = get_origin(tp)
    if origin in (list, tuple) and isinstance(value, ListConfig):
        args = get_args(tp)
        elem_tp = _unwrap_optional(args[0]) if args else Any
        if is_dataclass(elem_tp):
            items = [from_config(elem_tp, v) for v in value]
            return tuple(items) if origin is tuple else items

    # Any remaining OmegaConf container -> native Python, resolving interpolations.
    if isinstance(value, (DictConfig, ListConfig)):
        return OmegaConf.to_container(value, resolve=True)

    # Plain scalar (interpolations already resolved on access).
    return value


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def from_config(cls: Type[T], config: Any, *, strict: bool = False) -> T:
    """Instantiate dataclass ``cls`` from ``config``, deferring to field defaults.

    Args:
        cls: A dataclass type.
        config: An ``OmegaConf.DictConfig`` (or anything ``OmegaConf.create`` can
            wrap, e.g. a plain ``dict``).
        strict: If ``True``, raise ``ValueError`` when ``config`` carries keys that
            are not fields of ``cls``. Default ``False`` (extra keys ignored).

    Returns:
        An instance of ``cls``.

    Raises:
        TypeError: If ``cls`` is not a dataclass, or a required field (no default)
            is absent from ``config``.
        ValueError: If ``strict`` and unknown keys are present.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")

    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)

    hints = _resolve_hints(cls)
    kwargs: dict[str, Any] = {}

    for f in fields(cls):
        if not f.init:
            continue  # not a constructor argument
        # Skip absent or MISSING ("???") values so the field default applies.
        # The `in` check short-circuits, keeping `is_missing` safe.
        if f.name not in config or OmegaConf.is_missing(config, f.name):
            continue
        tp = hints.get(f.name, f.type)
        kwargs[f.name] = _convert(config[f.name], tp)

    if strict:
        known = {f.name for f in fields(cls)}
        unknown = [k for k in config.keys() if k not in known]
        if unknown:
            raise ValueError(
                f"Unknown config keys for {cls.__name__}: {sorted(unknown)}"
            )

    return cls(**kwargs)


class ConfigMixin:
    """Mixin adding a :meth:`from_config` classmethod to any dataclass.

    Inherit it alongside ``@dataclass``; instances are built via
    ``MyConfig.from_config(cfg)``.
    """

    @classmethod
    def from_config(cls: Type[T], config: Any, *, strict: bool = False) -> T:
        return from_config(cls, config, strict=strict)


def config_dataclass(cls: Type[T]) -> Type[T]:
    """Class decorator that injects :meth:`from_config` without inheritance.

    Useful when you'd rather not add a base class (e.g. to avoid MRO churn or to
    decorate dataclasses you don't own)::

        @config_dataclass
        @dataclass
        class TrainConfig:
            lr: float = 1e-3
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")

    def _from_config(c: Type[T], config: Any, *, strict: bool = False) -> T:
        return from_config(c, config, strict=strict)

    cls.from_config = classmethod(_from_config)  # type: ignore[attr-defined]
    return cls