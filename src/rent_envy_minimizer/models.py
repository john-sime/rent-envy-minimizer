from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Valuation:
    """A friend's raw monetary valuations of the three rooms."""

    room_1: Decimal
    room_2: Decimal
    room_3: Decimal


@dataclass(frozen=True)
class Premiums:
    """Premiums or discounts assigned to the three rooms."""

    room_1: Decimal
    room_2: Decimal
    room_3: Decimal

    def __post_init__(self) -> None:
        if self.room_1 + self.room_2 + self.room_3 != Decimal("0"):
            raise ValueError("Room premiums must sum to zero.")


@dataclass(frozen=True)
class Allocation:
    """
    Room allocation for the three friends.

    Each value is the room number allocated to that friend.
    """

    friend_1: int
    friend_2: int
    friend_3: int

    def __post_init__(self) -> None:
        rooms = (self.friend_1, self.friend_2, self.friend_3)

        if sorted(rooms) != [1, 2, 3]:
            raise ValueError("An allocation must assign rooms 1, 2, and 3 exactly once.")


@dataclass(frozen=True)
class AllocationResult:
    """Optimal result found for a particular room allocation."""

    allocation: Allocation
    premiums: Premiums
    maximum_envy: Decimal


@dataclass(frozen=True)
class SolverResult:
    """Complete result from evaluating all six room allocations."""

    recommended: AllocationResult
    allocation_results: tuple[AllocationResult, ...]
    tied_best_results: tuple[AllocationResult, ...]

    @property
    def has_tie(self) -> bool:
        """Return whether multiple allocations share the best objective value."""
        return len(self.tied_best_results) > 1
