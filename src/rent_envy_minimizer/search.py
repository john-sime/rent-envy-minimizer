from collections.abc import Iterable
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from rent_envy_minimizer.envy import maximum_envy
from rent_envy_minimizer.models import Allocation, AllocationResult, Premiums

COARSE_STEP = Decimal("10")
FINE_STEP = Decimal("1")


def _premium_bounds(rent: Decimal) -> tuple[Decimal, Decimal]:
    """
    Return the minimum and maximum valid premium for any room.

    Each room's rent is:

        rent / 3 + premium

    Requiring room rent to remain between zero and the total property rent
    gives:

        -rent / 3 <= premium <= 2 * rent / 3
    """
    if rent <= Decimal("0"):
        raise ValueError("Rent must be greater than zero.")

    base_share = rent / Decimal("3")
    lower_bound = -base_share
    upper_bound = rent - base_share

    return lower_bound, upper_bound


def _grid_values(
    lower_bound: Decimal,
    upper_bound: Decimal,
    step: Decimal,
) -> tuple[Decimal, ...]:
    """Return all multiples of step within the inclusive bounds."""
    if step <= Decimal("0"):
        raise ValueError("Grid step must be greater than zero.")

    first_multiplier = (lower_bound / step).to_integral_value(rounding=ROUND_CEILING)
    last_multiplier = (upper_bound / step).to_integral_value(rounding=ROUND_FLOOR)

    first = first_multiplier * step
    last = last_multiplier * step

    if first > last:
        return ()

    values: list[Decimal] = []
    current = first

    while current <= last:
        values.append(current)
        current += step

    return tuple(values)


def _premiums_within_bounds(
    premiums: Premiums,
    lower_bound: Decimal,
    upper_bound: Decimal,
) -> bool:
    """Return whether all three room premiums lie within the valid bounds."""
    return all(
        lower_bound <= premium <= upper_bound
        for premium in (
            premiums.room_1,
            premiums.room_2,
            premiums.room_3,
        )
    )


def _candidate_premiums(
    room_1: Decimal,
    room_2: Decimal,
) -> Premiums:
    """Create a zero-sum premium split from the first two room premiums."""
    room_3 = -(room_1 + room_2)

    return Premiums(
        room_1=room_1,
        room_2=room_2,
        room_3=room_3,
    )


def _evaluate_candidates(
    *,
    candidate_pairs: Iterable[tuple[Decimal, Decimal]],
    friend_1_premiums: Premiums,
    friend_2_premiums: Premiums,
    friend_3_premiums: Premiums,
    allocation: Allocation,
    lower_bound: Decimal,
    upper_bound: Decimal,
) -> tuple[Decimal, tuple[Premiums, ...]]:
    """
    Evaluate candidate premium pairs and retain every tied optimum.

    Each input pair represents room_1 and room_2. room_3 is derived from
    the zero-sum constraint.
    """
    best_envy: Decimal | None = None
    best_premiums: list[Premiums] = []

    for room_1, room_2 in candidate_pairs:
        premiums = _candidate_premiums(
            room_1=room_1,
            room_2=room_2,
        )

        if not _premiums_within_bounds(
            premiums=premiums,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        ):
            continue

        envy = maximum_envy(
            friend_1_premiums=friend_1_premiums,
            friend_2_premiums=friend_2_premiums,
            friend_3_premiums=friend_3_premiums,
            actual_premiums=premiums,
            allocation=allocation,
        )

        if best_envy is None or envy < best_envy:
            best_envy = envy
            best_premiums = [premiums]
        elif envy == best_envy:
            best_premiums.append(premiums)

    if best_envy is None:
        raise RuntimeError("No valid premium combinations were found.")

    return best_envy, tuple(best_premiums)


def _coarse_candidates(
    lower_bound: Decimal,
    upper_bound: Decimal,
) -> Iterable[tuple[Decimal, Decimal]]:
    """Generate the complete valid two-dimensional coarse search grid."""
    values = _grid_values(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        step=COARSE_STEP,
    )

    for room_1 in values:
        for room_2 in values:
            yield room_1, room_2


def _fine_candidates(
    *,
    coarse_optima: tuple[Premiums, ...],
    lower_bound: Decimal,
    upper_bound: Decimal,
) -> tuple[tuple[Decimal, Decimal], ...]:
    """
    Generate the union of fine-grid neighbourhoods around all coarse optima.

    Each coarse optimum is refined within one coarse step in both searched
    dimensions. Overlapping neighbourhoods are de-duplicated.
    """
    candidates: set[tuple[Decimal, Decimal]] = set()

    for premiums in coarse_optima:
        room_1_lower = max(
            lower_bound,
            premiums.room_1 - COARSE_STEP,
        )
        room_1_upper = min(
            upper_bound,
            premiums.room_1 + COARSE_STEP,
        )
        room_2_lower = max(
            lower_bound,
            premiums.room_2 - COARSE_STEP,
        )
        room_2_upper = min(
            upper_bound,
            premiums.room_2 + COARSE_STEP,
        )

        room_1_values = _grid_values(
            lower_bound=room_1_lower,
            upper_bound=room_1_upper,
            step=FINE_STEP,
        )
        room_2_values = _grid_values(
            lower_bound=room_2_lower,
            upper_bound=room_2_upper,
            step=FINE_STEP,
        )

        for room_1 in room_1_values:
            for room_2 in room_2_values:
                candidates.add((room_1, room_2))

    return tuple(sorted(candidates))


def _distance_squared(
    first: Premiums,
    second: Premiums,
) -> Decimal:
    """Return squared Euclidean distance between two premium splits."""
    room_1_difference = first.room_1 - second.room_1
    room_2_difference = first.room_2 - second.room_2
    room_3_difference = first.room_3 - second.room_3

    return room_1_difference**2 + room_2_difference**2 + room_3_difference**2


def _midpoint(
    first: Premiums,
    second: Premiums,
) -> Premiums:
    """Return the midpoint of two zero-sum premium splits."""
    room_1 = (first.room_1 + second.room_1) / Decimal("2")
    room_2 = (first.room_2 + second.room_2) / Decimal("2")
    room_3 = -(room_1 + room_2)

    return Premiums(
        room_1=room_1,
        room_2=room_2,
        room_3=room_3,
    )


def _representative_optimum(
    optima: tuple[Premiums, ...],
) -> Premiums:
    """
    Select a representative premium split from tied fine-grid optima.

    If there is only one optimum, return it directly.

    Otherwise, find the two optimal grid points furthest apart and return
    their midpoint. This represents the centre of the widest discovered
    optimal continuum and allows half-pound results where appropriate.
    """
    if not optima:
        raise ValueError("At least one optimum is required.")

    if len(optima) == 1:
        return optima[0]

    ordered_optima = tuple(
        sorted(
            optima,
            key=lambda premiums: (
                premiums.room_1,
                premiums.room_2,
                premiums.room_3,
            ),
        )
    )

    widest_first = ordered_optima[0]
    widest_second = ordered_optima[1]
    widest_distance = _distance_squared(
        widest_first,
        widest_second,
    )

    for index, first in enumerate(ordered_optima):
        for second in ordered_optima[index + 1 :]:
            distance = _distance_squared(first, second)

            if distance > widest_distance:
                widest_first = first
                widest_second = second
                widest_distance = distance

    return _midpoint(
        first=widest_first,
        second=widest_second,
    )


def search_allocation(
    *,
    friend_1_premiums: Premiums,
    friend_2_premiums: Premiums,
    friend_3_premiums: Premiums,
    allocation: Allocation,
    rent: Decimal,
) -> AllocationResult:
    """
    Find the premium split that minimises maximum envy for one allocation.

    The search runs in two stages:

    1. Exhaustive £10 grid search across the full valid premium space.
    2. Exhaustive £1 search around every tied coarse-grid optimum.

    If several fine-grid premium splits are equally optimal, a representative
    midpoint is selected from the widest span of tied optima.
    """
    lower_bound, upper_bound = _premium_bounds(rent)

    _, coarse_optima = _evaluate_candidates(
        candidate_pairs=_coarse_candidates(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        ),
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        allocation=allocation,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )

    fine_candidates = _fine_candidates(
        coarse_optima=coarse_optima,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )

    _, fine_optima = _evaluate_candidates(
        candidate_pairs=fine_candidates,
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        allocation=allocation,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )

    representative = _representative_optimum(fine_optima)

    representative_envy = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=representative,
        allocation=allocation,
    )

    return AllocationResult(
        allocation=allocation,
        premiums=representative,
        maximum_envy=representative_envy,
    )
