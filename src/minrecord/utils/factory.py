r"""Contain a function to instantiate an object from a configuration of
an expected type."""

from __future__ import annotations

__all__ = ["instantiate"]

from typing import Any, TypeVar

from coola.factory import OBJECT_TARGET, factory, is_object_config

T = TypeVar("T")


def instantiate(config: dict[str, Any], cls: type[T]) -> T:
    r"""Instantiate an object from its configuration, if the object is
    of the expected type.

    The object named by ``_target_`` is imported and checked to be a
    subclass of ``cls`` **before** it is called, so a configuration
    cannot call any other importable function. The module of
    ``_target_`` is imported, so a configuration from an untrusted
    source can still run the top-level code of a module.

    Args:
        config: The configuration of the object. It must have the key
            ``_target_`` and the arguments of the constructor, as the
            output of ``to_dict``. It is not modified.
        cls: The expected class of the object. The class named by
            ``_target_`` must be ``cls`` or a subclass of ``cls``.

    Returns:
        The instantiated object.

    Raises:
        TypeError: if ``config`` is not a ``dict``, or if it is not a
            configuration of ``cls`` (the key ``_target_`` is missing, or it names an object
            that is not ``cls`` or a subclass of ``cls``).
        ImportError: if the object named by ``_target_`` cannot be
            imported.

    Example:
        ```pycon
        >>> from minrecord import BaseRecord
        >>> from minrecord.utils.factory import instantiate
        >>> record = instantiate(
        ...     {"_target_": "minrecord.Record", "name": "loss", "max_size": 5}, BaseRecord
        ... )
        >>> record
        Record(name=loss, max_size=5, size=0)

        ```
    """
    if not isinstance(config, dict):
        msg = f"Expected the configuration of a {cls.__qualname__} (a dict), got {config!r:.80}"
        raise TypeError(msg)
    if not is_object_config(config, cls, import_target=True):
        msg = (
            f"The configuration {config.get(OBJECT_TARGET)!r} is not a configuration "
            f"of {cls.__qualname__}"
        )
        raise TypeError(msg)
    return factory(**config)
