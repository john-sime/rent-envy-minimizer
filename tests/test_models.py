from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from rent_envy_minimizer.models import (
    Allocation,
    AllocationResult,
    Premiums,
    Valuation,
)


def test_valuation_stores_room_values() -> None:
    valuation = Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )

    assert valuation.room_1 == Decimal("1200")
    assert valuation.room_2 == Decimal("1000")
    assert valuation.room_3 == Decimal("800")


def test_valuation_is_immutable() -> None:
    valuation = Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )

    with pytest.raises(FrozenInstanceError):
        valuation.__setattr__("room_1", Decimal("1300"))


def test_premiums_accept_zero_sum_values() -> None:
    premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("-50"),
        room_3=Decimal("-50"),
    )

    assert premiums.room_1 == Decimal("100")
    assert premiums.room_2 == Decimal("-50")
    assert premiums.room_3 == Decimal("-50")


def test_premiums_accept_fractional_zero_sum_values() -> None:
    premiums = Premiums(
        room_1=Decimal("137.50"),
        room_2=Decimal("-42.50"),
        room_3=Decimal("-95.00"),
    )

    assert sum(
        (premiums.room_1, premiums.room_2, premiums.room_3),
        start=Decimal("0"),
    ) == Decimal("0")


def test_premiums_reject_non_zero_sum_values() -> None:
    with pytest.raises(ValueError, match="Room premiums must sum to zero"):
        Premiums(
            room_1=Decimal("100"),
            room_2=Decimal("-40"),
            room_3=Decimal("-50"),
        )


@pytest.mark.parametrize(
    ("friend_1", "friend_2", "friend_3"),
    [
        (1, 2, 3),
        (1, 3, 2),
        (2, 1, 3),
        (2, 3, 1),
        (3, 1, 2),
        (3, 2, 1),
    ],
)
def test_allocation_accepts_all_six_valid_room_configurations(
    friend_1: int,
    friend_2: int,
    friend_3: int,
) -> None:
    allocation = Allocation(
        friend_1=friend_1,
        friend_2=friend_2,
        friend_3=friend_3,
    )

    assert allocation.friend_1 == friend_1
    assert allocation.friend_2 == friend_2
    assert allocation.friend_3 == friend_3


@pytest.mark.parametrize(
    ("friend_1", "friend_2", "friend_3"),
    [
        (1, 1, 2),
        (1, 2, 2),
        (3, 3, 3),
        (0, 1, 2),
        (1, 2, 4),
    ],
)
def test_allocation_rejects_invalid_room_configurations(
    friend_1: int,
    friend_2: int,
    friend_3: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="An allocation must assign rooms 1, 2, and 3 exactly once",
    ):
        Allocation(
            friend_1=friend_1,
            friend_2=friend_2,
            friend_3=friend_3,
        )


def test_allocation_result_stores_optimisation_result() -> None:
    allocation = Allocation(
        friend_1=2,
        friend_2=1,
        friend_3=3,
    )
    premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("-50"),
        room_3=Decimal("-100"),
    )

    result = AllocationResult(
        allocation=allocation,
        premiums=premiums,
        maximum_envy=Decimal("-18"),
    )

    assert result.allocation == allocation
    assert result.premiums == premiums
    assert result.maximum_envy == Decimal("-18")
