from decimal import Decimal
from itertools import permutations

from rent_envy_minimizer.models import (
    Allocation,
    AllocationResult,
    SolverResult,
    Valuation,
)
from rent_envy_minimizer.search import search_allocation
from rent_envy_minimizer.valuations import valuation_to_premiums


def _all_allocations() -> tuple[Allocation, ...]:
    """
    Return all six possible allocations in deterministic order.

    Ordering is lexicographic by the rooms assigned to friend_1,
    friend_2, then friend_3. This ordering also supports the specified
    tie-break rule of preferring lower-indexed friends in lower-indexed
    rooms where equivalent solutions exist.
    """
    return tuple(
        Allocation(
            friend_1=room_assignment[0],
            friend_2=room_assignment[1],
            friend_3=room_assignment[2],
        )
        for room_assignment in permutations((1, 2, 3))
    )


def _allocation_sort_key(
    result: AllocationResult,
) -> tuple[int, int, int]:
    """Return the deterministic tie-break key for an allocation result."""
    return (
        result.allocation.friend_1,
        result.allocation.friend_2,
        result.allocation.friend_3,
    )


def solve(
    *,
    friend_1_valuation: Valuation,
    friend_2_valuation: Valuation,
    friend_3_valuation: Valuation,
    rent: Decimal,
) -> SolverResult:
    """
    Find the globally preferred room allocation and rent premiums.

    Each friend's raw room valuations are first normalised into subjective
    zero-sum premiums.

    The optimiser then evaluates all six possible room allocations. For each
    allocation, it finds the room premium split that minimises maximum envy.

    The allocation with the lowest achievable maximum envy is recommended.

    If multiple allocations achieve exactly the same minimum maximum envy,
    the lexicographically lowest allocation is selected deterministically.
    All tied best results are retained so the caller can report the tie.
    """
    friend_1_premiums = valuation_to_premiums(friend_1_valuation)
    friend_2_premiums = valuation_to_premiums(friend_2_valuation)
    friend_3_premiums = valuation_to_premiums(friend_3_valuation)

    allocation_results = tuple(
        search_allocation(
            friend_1_premiums=friend_1_premiums,
            friend_2_premiums=friend_2_premiums,
            friend_3_premiums=friend_3_premiums,
            allocation=allocation,
            rent=rent,
        )
        for allocation in _all_allocations()
    )

    best_maximum_envy = min(result.maximum_envy for result in allocation_results)

    tied_best_results = tuple(
        result for result in allocation_results if result.maximum_envy == best_maximum_envy
    )

    recommended = min(
        tied_best_results,
        key=_allocation_sort_key,
    )

    return SolverResult(
        recommended=recommended,
        allocation_results=allocation_results,
        tied_best_results=tied_best_results,
    )
