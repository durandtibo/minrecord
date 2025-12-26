from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from minrecord.config import Config, get_default_config

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _reset_default_config() -> Generator[None, None, None]:
    """Reset the config before and after each test."""
    if hasattr(get_default_config, "_config"):
        del get_default_config._config
    yield
    if hasattr(get_default_config, "_config"):
        del get_default_config._config


############################
#     Tests for Config     #
############################


def test_config_init_default_max_size() -> None:
    """Test that Config initializes with the default max_size."""
    assert Config().get_max_size() == Config.DEFAULT_MAX_SIZE


def test_config_init_default_max_size_value() -> None:
    """Test that the default max_size is 10."""
    assert Config().get_max_size() == 10


def test_config_get_max_size() -> None:
    """Test getting the max_size."""
    assert Config().get_max_size() == 10


def test_config_set_max_size_valid() -> None:
    """Test setting max_size to a valid positive integer."""
    config = Config()
    config.set_max_size(5)
    assert config.get_max_size() == 5


def test_config_set_max_size_one() -> None:
    """Test setting max_size to 1."""
    config = Config()
    config.set_max_size(1)
    assert config.get_max_size() == 1


def test_config_set_max_size_large_value() -> None:
    """Test setting max_size to a large value."""
    config = Config()
    config.set_max_size(1000)
    assert config.get_max_size() == 1000


def test_config_set_max_size_zero_raises_value_error() -> None:
    """Test that setting max_size to 0 raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 0"):
        config.set_max_size(0)


def test_config_set_max_size_negative_raises_value_error() -> None:
    """Test that setting max_size to a negative integer raises
    ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got -1"):
        config.set_max_size(-1)


def test_config_set_max_size_float_raises_value_error() -> None:
    """Test that setting max_size to a float raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 5.5"):
        config.set_max_size(5.5)


def test_config_set_max_size_string_raises_value_error() -> None:
    """Test that setting max_size to a string raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got 10"):
        config.set_max_size("10")


def test_config_set_max_size_none_raises_value_error() -> None:
    """Test that setting max_size to None raises ValueError."""
    config = Config()
    with pytest.raises(ValueError, match=r"max_size must be a positive integer, got None"):
        config.set_max_size(None)


def test_config_reset_max_size() -> None:
    """Test resetting max_size to the default value."""
    config = Config()
    config.set_max_size(5)
    assert config.get_max_size() == 5
    config.reset_max_size()
    assert config.get_max_size() == Config.DEFAULT_MAX_SIZE


def test_config_reset_max_size_to_ten() -> None:
    """Test that reset_max_size resets to 10."""
    config = Config()
    config.set_max_size(20)
    config.reset_max_size()
    assert config.get_max_size() == 10


def test_config_reset_max_size_when_already_default() -> None:
    """Test resetting max_size when it's already at the default
    value."""
    config = Config()
    config.reset_max_size()
    assert config.get_max_size() == Config.DEFAULT_MAX_SIZE


def test_config_multiple_set_operations() -> None:
    """Test multiple set_max_size operations in sequence."""
    config = Config()
    config.set_max_size(5)
    assert config.get_max_size() == 5
    config.set_max_size(15)
    assert config.get_max_size() == 15
    config.set_max_size(3)
    assert config.get_max_size() == 3


def test_config_set_reset_set() -> None:
    """Test setting, resetting, then setting again."""
    config = Config()
    config.set_max_size(7)
    assert config.get_max_size() == 7
    config.reset_max_size()
    assert config.get_max_size() == 10
    config.set_max_size(12)
    assert config.get_max_size() == 12


def test_config_independence_between_instances() -> None:
    """Test that different Config instances are independent."""
    config1 = Config()
    config2 = Config()

    config1.set_max_size(5)
    assert config1.get_max_size() == 5
    assert config2.get_max_size() == 10

    config2.set_max_size(15)
    assert config1.get_max_size() == 5
    assert config2.get_max_size() == 15


########################################
#     Tests for get_default_config     #
########################################


def test_returns_config_instance() -> None:
    """Test that the function returns a Config instance."""
    assert isinstance(get_default_config(), Config)


def test_singleton_pattern() -> None:
    """Test that the same instance is returned on multiple calls."""
    config1 = get_default_config()
    config2 = get_default_config()

    assert config1 is config2


def test_lazy_initialization() -> None:
    """Test that config is created lazily on first call."""
    # Before first call, _config attribute should not exist
    assert not hasattr(get_default_config, "_config")

    # After first call, it should exist
    get_default_config()
    assert hasattr(get_default_config, "_config")


def test_modifications_persist() -> None:
    """Test that modifications to the config persist across calls."""
    config1 = get_default_config()

    # Modify the config
    config1.set_max_size(123)

    # Get config again and verify the change persisted
    config2 = get_default_config()
    assert config2.get_max_size() == 123


def test_different_from_new_config_instance() -> None:
    """Test that the singleton differs from a newly created Config."""
    assert get_default_config() is not Config()


def test_state_isolation_from_new_instances() -> None:
    """Test that changes to singleton don't affect new Config
    instances."""
    singleton = get_default_config()

    # Modify singleton
    singleton.set_max_size(123)

    # New instance should have default value, not modified value
    assert Config().get_max_size() == 10


def test_attribute_storage_location() -> None:
    """Test that the config is stored as a function attribute."""
    config = get_default_config()

    assert hasattr(get_default_config, "_config")
    assert get_default_config._config is config
