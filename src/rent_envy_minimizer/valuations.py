from decimal import Decimal

from rent_envy_minimizer.models import Premiums, Valuation

ROOM_COUNT = Decimal("3")


def valuation_to_premiums(valuation: Valuation) -> Premiums:
    """
    Convert a friend's raw room valuations into zero-sum subjective premiums.

    Each room's premium is its valuation relative to the mean valuation of
    that friend's three rooms.

    The third premium is derived from the first two so that the zero-sum
    invariant is preserved exactly, including when the mean is a repeating
    decimal.
    """
    total = valuation.room_1 + valuation.room_2 + valuation.room_3
    mean = total / ROOM_COUNT

    room_1 = valuation.room_1 - mean
    room_2 = valuation.room_2 - mean
    room_3 = -(room_1 + room_2)

    return Premiums(
        room_1=room_1,
        room_2=room_2,
        room_3=room_3,
    )
