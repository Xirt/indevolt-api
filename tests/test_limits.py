"""Scenarios for the existing generation-specific parameter checks."""

from collections.abc import Callable

import pytest

from indevolt_api import IndevoltAPI, PowerExceedsMaxError, SocBelowMinimumError

LimitCheck = Callable[[IndevoltAPI, int, int, int], None]

pytestmark = pytest.mark.parametrize(
    ("check_limit", "generation", "max_power"),
    [
        pytest.param(IndevoltAPI.check_charge_limits, 1, 1200, id="gen1-charge"),
        pytest.param(IndevoltAPI.check_discharge_limits, 1, 800, id="gen1-discharge"),
        pytest.param(IndevoltAPI.check_charge_limits, 2, 10800, id="gen2-charge"),
        pytest.param(IndevoltAPI.check_discharge_limits, 2, 10800, id="gen2-discharge"),
    ],
)


@pytest.mark.parametrize("offset", [-1, 0], ids=["below-maximum", "at-maximum"])
def test_power_within_limit(
    api_without_network: IndevoltAPI,
    check_limit: LimitCheck,
    generation: int,
    max_power: int,
    offset: int,
) -> None:
    """The maximum power and minimum SOC are inclusive boundaries."""
    check_limit(api_without_network, max_power + offset, 5, generation)


def test_power_above_limit(
    api_without_network: IndevoltAPI,
    check_limit: LimitCheck,
    generation: int,
    max_power: int,
) -> None:
    """Excess power raises an exception carrying the applicable limit."""
    with pytest.raises(PowerExceedsMaxError) as exc:
        check_limit(api_without_network, max_power + 1, 5, generation)

    assert exc.value.power == max_power + 1
    assert exc.value.max_power == max_power
    assert exc.value.generation == generation


def test_soc_below_minimum(
    api_without_network: IndevoltAPI,
    check_limit: LimitCheck,
    generation: int,
    max_power: int,
) -> None:
    """SOC below five percent raises an exception with the minimum."""
    with pytest.raises(SocBelowMinimumError) as exc:
        check_limit(api_without_network, max_power, 4, generation)

    assert exc.value.target_soc == 4
    assert exc.value.minimum_soc == 5
    assert exc.value.generation == generation
