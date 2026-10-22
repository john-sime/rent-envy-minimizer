from decimal import Decimal

from rent_envy_minimizer.models import Valuation
from rent_envy_minimizer.valuations import valuation_to_premiums


def test_valuation_to_premiums_converts_simple_values() -> None:
    valuation = Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )

    premiums = valuation_to_premiums(valuation)

    assert premiums.room_1 == Decimal("200")
    assert premiums.room_2 == Decimal("0")
    assert premiums.room_3 == Decimal("-200")


def test_valuation_to_premiums_uses_friends_own_mean() -> None:
    valuation = Valuation(
        room_1=Decimal("1500"),
        room_2=Decimal("1200"),
        room_3=Decimal("900"),
    )

    premiums = valuation_to_premiums(valuation)

    assert premiums.room_1 == Decimal("300")
    assert premiums.room_2 == Decimal("0")
    assert premiums.room_3 == Decimal("-300")


def test_valuation_to_premiums_handles_non_symmetric_values() -> None:
    valuation = Valuation(
        room_1=Decimal("1400"),
        room_2=Decimal("1000"),
        room_3=Decimal("900"),
    )

    premiums = valuation_to_premiums(valuation)

    assert premiums.room_1 == Decimal("300")
    assert premiums.room_2 == Decimal("-100")
    assert premiums.room_3 == Decimal("-200")


def test_adding_same_amount_to_every_room_does_not_change_premiums() -> None:
    original = Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )
    shifted = Valuation(
        room_1=Decimal("1700"),
        room_2=Decimal("1500"),
        room_3=Decimal("1300"),
    )

    assert valuation_to_premiums(original) == valuation_to_premiums(shifted)


def test_different_total_valuations_can_produce_same_relative_premiums() -> None:
    first = Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )
    second = Valuation(
        room_1=Decimal("700"),
        room_2=Decimal("500"),
        room_3=Decimal("300"),
    )

    assert valuation_to_premiums(first) == valuation_to_premiums(second)


def test_premiums_sum_exactly_to_zero_when_mean_repeats() -> None:
    valuation = Valuation(
        room_1=Decimal("1000"),
        room_2=Decimal("900"),
        room_3=Decimal("801"),
    )

    premiums = valuation_to_premiums(valuation)

    total = premiums.room_1 + premiums.room_2 + premiums.room_3

    assert total == Decimal("0")


def test_relative_room_difference_is_preserved() -> None:
    valuation = Valuation(
        room_1=Decimal("1250"),
        room_2=Decimal("1050"),
        room_3=Decimal("900"),
    )

    premiums = valuation_to_premiums(valuation)

    assert premiums.room_1 - premiums.room_2 == Decimal("200")
