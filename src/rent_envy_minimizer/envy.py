from decimal import Decimal

from rent_envy_minimizer.models import Allocation, Premiums


def _room_value(values: Premiums, room: int) -> Decimal:
    """Return the value associated with a numbered room."""
    match room:
        case 1:
            return values.room_1
        case 2:
            return values.room_2
        case 3:
            return values.room_3
        case _:
            raise ValueError(f"Invalid room number: {room}")


def deal_value(
    subjective_premiums: Premiums,
    actual_premiums: Premiums,
    room: int,
) -> Decimal:
    """
    Calculate how good a room's deal is from one friend's perspective.

    A positive result means the room is cheaper than the friend believes
    it should be. A negative result means it is more expensive.
    """
    subjective_value = _room_value(subjective_premiums, room)
    actual_price = _room_value(actual_premiums, room)

    return subjective_value - actual_price


def maximum_friend_envy(
    subjective_premiums: Premiums,
    actual_premiums: Premiums,
    allocated_room: int,
) -> Decimal:
    """
    Calculate one friend's maximum envy under a proposed rent split.

    Envy is the difference between the perceived deal value of an
    alternative room and the perceived deal value of the allocated room.

    The result is deliberately not clamped at zero. A negative result
    means the friend strictly prefers their allocated room to either
    alternative.
    """
    allocated_deal_value = deal_value(
        subjective_premiums=subjective_premiums,
        actual_premiums=actual_premiums,
        room=allocated_room,
    )

    alternative_envies = [
        deal_value(
            subjective_premiums=subjective_premiums,
            actual_premiums=actual_premiums,
            room=room,
        )
        - allocated_deal_value
        for room in (1, 2, 3)
        if room != allocated_room
    ]

    return max(alternative_envies)


def maximum_envy(
    friend_1_premiums: Premiums,
    friend_2_premiums: Premiums,
    friend_3_premiums: Premiums,
    actual_premiums: Premiums,
    allocation: Allocation,
) -> Decimal:
    """
    Calculate the maximum envy experienced by any friend.

    This is the objective value that the search algorithm will minimise.
    """
    friend_envies = (
        maximum_friend_envy(
            subjective_premiums=friend_1_premiums,
            actual_premiums=actual_premiums,
            allocated_room=allocation.friend_1,
        ),
        maximum_friend_envy(
            subjective_premiums=friend_2_premiums,
            actual_premiums=actual_premiums,
            allocated_room=allocation.friend_2,
        ),
        maximum_friend_envy(
            subjective_premiums=friend_3_premiums,
            actual_premiums=actual_premiums,
            allocated_room=allocation.friend_3,
        ),
    )

    return max(friend_envies)
