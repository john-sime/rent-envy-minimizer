from decimal import Decimal

import pytest

from rent_envy_minimizer.envy import (
    deal_value,
    maximum_envy,
    maximum_friend_envy,
)
from rent_envy_minimizer.models import Allocation, Premiums


def _example_test_1() -> Decimal:
    subjective_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("0"),
        room_3=Decimal("-200"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("25"),
        room_3=Decimal("-175"),
    )

    result = maximum_friend_envy(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        allocated_room=2,
    )

    return result


def _example_test_2() -> Decimal:
    subjective_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("-20"),
        room_3=Decimal("-80"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("50"),
        room_2=Decimal("0"),
        room_3=Decimal("-50"),
    )

    result = maximum_friend_envy(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        allocated_room=1,
    )

    return result


def test_deal_value_is_positive_when_room_is_cheaper_than_subjective_value() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("0"),
        room_3=Decimal("-200"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("25"),
        room_3=Decimal("-175"),
    )

    result = deal_value(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        room=1,
    )

    assert result == Decimal("50")


def test_deal_value_is_negative_when_room_is_more_expensive_than_subjective_value() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("0"),
        room_3=Decimal("-200"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("25"),
        room_3=Decimal("-175"),
    )

    result = deal_value(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        room=2,
    )

    assert result == Decimal("-25")


def test_deal_value_is_zero_when_actual_and_subjective_premiums_match() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )

    result = deal_value(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        room=3,
    )

    assert result == Decimal("0")


@pytest.mark.parametrize(
    ("room", "expected"),
    [
        (1, Decimal("50")),
        (2, Decimal("-25")),
        (3, Decimal("-25")),
    ],
)
def test_deal_value_selects_correct_room(
    room: int,
    expected: Decimal,
) -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("0"),
        room_3=Decimal("-200"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("25"),
        room_3=Decimal("-175"),
    )

    result = deal_value(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        room=room,
    )

    assert result == expected


@pytest.mark.parametrize("room", [0, 4, -1, 99])
def test_deal_value_rejects_invalid_room_number(room: int) -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )

    with pytest.raises(ValueError, match=f"Invalid room number: {room}"):
        deal_value(
            subjective_premiums=subjective_premiums,
            actual_premiums=actual_premiums,
            room=room,
        )


def test_maximum_friend_envy_matches_alice_example() -> None:
    result = _example_test_1()

    assert result == Decimal("75")


def test_maximum_friend_envy_uses_most_attractive_alternative() -> None:
    result = _example_test_1()

    room_1_envy = Decimal("50") - Decimal("-25")
    room_3_envy = Decimal("-25") - Decimal("-25")

    assert room_1_envy == Decimal("75")
    assert room_3_envy == Decimal("0")
    assert result == max(room_1_envy, room_3_envy)


def test_maximum_friend_envy_can_be_zero() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )

    result = maximum_friend_envy(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        allocated_room=1,
    )

    assert result == Decimal("0")


def test_maximum_friend_envy_can_be_negative() -> None:
    result = _example_test_2()

    assert result == Decimal("-70")


def test_maximum_friend_envy_is_not_clamped_to_zero() -> None:
    result = _example_test_2()

    assert result < Decimal("0")


@pytest.mark.parametrize(
    ("allocated_room", "expected"),
    [
        (1, Decimal("-75")),
        (2, Decimal("75")),
        (3, Decimal("75")),
    ],
)
def test_maximum_friend_envy_handles_each_allocated_room(
    allocated_room: int,
    expected: Decimal,
) -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("0"),
        room_3=Decimal("-200"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("25"),
        room_3=Decimal("-175"),
    )

    result = maximum_friend_envy(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        allocated_room=allocated_room,
    )

    assert result == expected


def test_maximum_friend_envy_rejects_invalid_allocated_room() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )

    with pytest.raises(ValueError, match="Invalid room number: 4"):
        maximum_friend_envy(
            subjective_premiums=subjective_premiums,
            actual_premiums=actual_premiums,
            allocated_room=4,
        )


def test_maximum_envy_returns_worst_positive_friend_envy() -> None:
    friend_1_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("50"),
        room_2=Decimal("0"),
        room_3=Decimal("-50"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("-50"),
        room_2=Decimal("-50"),
        room_3=Decimal("100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=actual_premiums,
        allocation=allocation,
    )

    assert result == Decimal("50")


def test_maximum_envy_can_be_negative_when_every_friend_prefers_own_room() -> None:
    friend_1_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("-50"),
        room_2=Decimal("100"),
        room_3=Decimal("-50"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("-40"),
        room_2=Decimal("-60"),
        room_3=Decimal("100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=actual_premiums,
        allocation=allocation,
    )

    assert result == Decimal("-100")


def test_maximum_envy_can_be_zero() -> None:
    friend_1_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=actual_premiums,
        allocation=allocation,
    )

    assert result == Decimal("0")


def test_maximum_envy_respects_non_identity_allocation() -> None:
    friend_1_premiums = Premiums(
        room_1=Decimal("-50"),
        room_2=Decimal("100"),
        room_3=Decimal("-50"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("-50"),
        room_2=Decimal("-50"),
        room_3=Decimal("100"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("-50"),
        room_3=Decimal("-50"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=2,
        friend_2=3,
        friend_3=1,
    )

    result = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=actual_premiums,
        allocation=allocation,
    )

    assert result == Decimal("-150")


def test_maximum_envy_uses_all_three_friends() -> None:
    friend_1_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("-50"),
        room_2=Decimal("100"),
        room_3=Decimal("-50"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("-100"),
        room_3=Decimal("-100"),
    )
    actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    friend_1_envy = maximum_friend_envy(
        subjective_premiums=friend_1_premiums,
        actual_premiums=actual_premiums,
        allocated_room=1,
    )
    friend_2_envy = maximum_friend_envy(
        subjective_premiums=friend_2_premiums,
        actual_premiums=actual_premiums,
        allocated_room=2,
    )
    friend_3_envy = maximum_friend_envy(
        subjective_premiums=friend_3_premiums,
        actual_premiums=actual_premiums,
        allocated_room=3,
    )

    result = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=actual_premiums,
        allocation=allocation,
    )

    assert friend_1_envy == Decimal("-100")
    assert friend_2_envy == Decimal("-150")
    assert friend_3_envy == Decimal("300")
    assert result == Decimal("300")


def test_changing_actual_premiums_changes_envy() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("0"),
        room_3=Decimal("-200"),
    )
    equal_actual_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    adjusted_actual_premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("25"),
        room_3=Decimal("-175"),
    )

    equal_price_envy = maximum_friend_envy(
        subjective_premiums=subjective_premiums,
        actual_premiums=equal_actual_premiums,
        allocated_room=2,
    )
    adjusted_price_envy = maximum_friend_envy(
        subjective_premiums=subjective_premiums,
        actual_premiums=adjusted_actual_premiums,
        allocated_room=2,
    )

    assert equal_price_envy == Decimal("200")
    assert adjusted_price_envy == Decimal("75")
    assert adjusted_price_envy < equal_price_envy


def test_identical_subjective_and_actual_premiums_produce_zero_envy_for_any_room() -> None:
    premiums = Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("-25"),
        room_3=Decimal("-125"),
    )

    for allocated_room in (1, 2, 3):
        result = maximum_friend_envy(
            subjective_premiums=premiums,
            actual_premiums=premiums,
            allocated_room=allocated_room,
        )

        assert result == Decimal("0")
