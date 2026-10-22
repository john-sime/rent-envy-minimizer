from decimal import Decimal

import pytest

from rent_envy_minimizer import search
from rent_envy_minimizer.envy import maximum_envy
from rent_envy_minimizer.models import Allocation, AllocationResult, Premiums


def _test_example_1() -> tuple[Premiums, Premiums, Premiums, Allocation]:
    friend_1_premiums = Premiums(
        room_1=Decimal("100"),
        room_2=Decimal("0"),
        room_3=Decimal("-100"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("100"),
        room_3=Decimal("-100"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("-100"),
        room_2=Decimal("0"),
        room_3=Decimal("100"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    return friend_1_premiums, friend_2_premiums, friend_3_premiums, allocation


def _test_example_2() -> tuple[Premiums, Premiums, Premiums, Premiums]:
    first = Premiums(
        room_1=Decimal("-4"),
        room_2=Decimal("0"),
        room_3=Decimal("4"),
    )
    middle = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    last = Premiums(
        room_1=Decimal("4"),
        room_2=Decimal("-2"),
        room_3=Decimal("-2"),
    )

    result = search._representative_optimum(
        (
            first,
            middle,
            last,
        )
    )

    return first, middle, last, result


def _test_example_3() -> tuple[Premiums, Allocation, AllocationResult]:
    subjective_premiums = Premiums(
        room_1=Decimal("13"),
        room_2=Decimal("-4"),
        room_3=Decimal("-9"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = search.search_allocation(
        friend_1_premiums=subjective_premiums,
        friend_2_premiums=subjective_premiums,
        friend_3_premiums=subjective_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    return subjective_premiums, allocation, result


def test_search_steps_are_expected_values() -> None:
    assert search.COARSE_STEP == Decimal("10")
    assert search.FINE_STEP == Decimal("1")


def test_premium_bounds_for_rent_divisible_by_three() -> None:
    lower_bound, upper_bound = search._premium_bounds(Decimal("300"))

    assert lower_bound == Decimal("-100")
    assert upper_bound == Decimal("200")


def test_premium_bounds_allow_room_to_have_zero_rent() -> None:
    rent = Decimal("300")

    lower_bound, _ = search._premium_bounds(rent)

    room_rent = rent / Decimal("3") + lower_bound

    assert room_rent == Decimal("0")


def test_premium_bounds_allow_one_room_to_carry_entire_rent() -> None:
    rent = Decimal("300")

    _, upper_bound = search._premium_bounds(rent)

    room_rent = rent / Decimal("3") + upper_bound

    assert room_rent == rent


def test_premium_bounds_for_rent_not_divisible_by_three() -> None:
    rent = Decimal("100")

    lower_bound, upper_bound = search._premium_bounds(rent)
    base_share = rent / Decimal("3")

    assert lower_bound == -base_share
    assert upper_bound == rent - base_share


@pytest.mark.parametrize(
    "rent",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("-300"),
    ],
)
def test_premium_bounds_reject_non_positive_rent(rent: Decimal) -> None:
    with pytest.raises(ValueError, match="Rent must be greater than zero"):
        search._premium_bounds(rent)


def test_grid_values_returns_multiples_of_step_within_bounds() -> None:
    values = search._grid_values(
        lower_bound=Decimal("-25"),
        upper_bound=Decimal("27"),
        step=Decimal("10"),
    )

    assert values == (
        Decimal("-20"),
        Decimal("-10"),
        Decimal("0"),
        Decimal("10"),
        Decimal("20"),
    )


def test_grid_values_includes_exact_boundaries() -> None:
    values = search._grid_values(
        lower_bound=Decimal("-20"),
        upper_bound=Decimal("20"),
        step=Decimal("10"),
    )

    assert values == (
        Decimal("-20"),
        Decimal("-10"),
        Decimal("0"),
        Decimal("10"),
        Decimal("20"),
    )


def test_grid_values_handles_one_pound_step() -> None:
    values = search._grid_values(
        lower_bound=Decimal("-2"),
        upper_bound=Decimal("2"),
        step=Decimal("1"),
    )

    assert values == (
        Decimal("-2"),
        Decimal("-1"),
        Decimal("0"),
        Decimal("1"),
        Decimal("2"),
    )


def test_grid_values_returns_empty_tuple_when_no_multiple_is_in_range() -> None:
    values = search._grid_values(
        lower_bound=Decimal("0.1"),
        upper_bound=Decimal("0.9"),
        step=Decimal("1"),
    )

    assert values == ()


@pytest.mark.parametrize(
    "step",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("-10"),
    ],
)
def test_grid_values_rejects_non_positive_step(step: Decimal) -> None:
    with pytest.raises(ValueError, match="Grid step must be greater than zero"):
        search._grid_values(
            lower_bound=Decimal("-10"),
            upper_bound=Decimal("10"),
            step=step,
        )


def test_candidate_premiums_derives_third_room_from_zero_sum_constraint() -> None:
    premiums = search._candidate_premiums(
        room_1=Decimal("150"),
        room_2=Decimal("-50"),
    )

    assert premiums == Premiums(
        room_1=Decimal("150"),
        room_2=Decimal("-50"),
        room_3=Decimal("-100"),
    )


def test_candidate_premiums_always_sum_to_zero() -> None:
    premiums = search._candidate_premiums(
        room_1=Decimal("37"),
        room_2=Decimal("-12"),
    )

    assert premiums.room_1 + premiums.room_2 + premiums.room_3 == Decimal("0")


def test_premiums_within_bounds_accepts_values_on_boundaries() -> None:
    premiums = Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("-100"),
        room_3=Decimal("-100"),
    )

    result = search._premiums_within_bounds(
        premiums=premiums,
        lower_bound=Decimal("-100"),
        upper_bound=Decimal("200"),
    )

    assert result is True


def test_premiums_within_bounds_rejects_room_below_lower_bound() -> None:
    premiums = Premiums(
        room_1=Decimal("201"),
        room_2=Decimal("-101"),
        room_3=Decimal("-100"),
    )

    result = search._premiums_within_bounds(
        premiums=premiums,
        lower_bound=Decimal("-100"),
        upper_bound=Decimal("200"),
    )

    assert result is False


def test_premiums_within_bounds_rejects_room_above_upper_bound() -> None:
    premiums = Premiums(
        room_1=Decimal("201"),
        room_2=Decimal("-100"),
        room_3=Decimal("-101"),
    )

    result = search._premiums_within_bounds(
        premiums=premiums,
        lower_bound=Decimal("-150"),
        upper_bound=Decimal("200"),
    )

    assert result is False


def test_coarse_candidates_generates_full_two_dimensional_grid() -> None:
    candidates = tuple(
        search._coarse_candidates(
            lower_bound=Decimal("-10"),
            upper_bound=Decimal("10"),
        )
    )

    assert len(candidates) == 9
    assert (Decimal("-10"), Decimal("-10")) in candidates
    assert (Decimal("-10"), Decimal("10")) in candidates
    assert (Decimal("0"), Decimal("0")) in candidates
    assert (Decimal("10"), Decimal("-10")) in candidates
    assert (Decimal("10"), Decimal("10")) in candidates


def test_evaluate_candidates_discards_candidate_with_invalid_derived_room_3() -> None:
    zero_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    best_envy, best_premiums = search._evaluate_candidates(
        candidate_pairs=[
            (Decimal("20"), Decimal("20")),
            (Decimal("0"), Decimal("0")),
        ],
        friend_1_premiums=zero_premiums,
        friend_2_premiums=zero_premiums,
        friend_3_premiums=zero_premiums,
        allocation=allocation,
        lower_bound=Decimal("-20"),
        upper_bound=Decimal("20"),
    )

    assert best_envy == Decimal("0")
    assert best_premiums == (
        Premiums(
            room_1=Decimal("0"),
            room_2=Decimal("0"),
            room_3=Decimal("0"),
        ),
    )


def test_evaluate_candidates_raises_when_every_candidate_is_invalid() -> None:
    zero_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    with pytest.raises(
        RuntimeError,
        match="No valid premium combinations were found",
    ):
        search._evaluate_candidates(
            candidate_pairs=[
                (Decimal("20"), Decimal("20")),
                (Decimal("-20"), Decimal("-20")),
            ],
            friend_1_premiums=zero_premiums,
            friend_2_premiums=zero_premiums,
            friend_3_premiums=zero_premiums,
            allocation=allocation,
            lower_bound=Decimal("-10"),
            upper_bound=Decimal("10"),
        )


def test_evaluate_candidates_retains_all_tied_optima() -> None:
    friend_1_premiums, friend_2_premiums, friend_3_premiums, allocation = _test_example_1()

    best_envy, best_premiums = search._evaluate_candidates(
        candidate_pairs=[
            (Decimal("0"), Decimal("0")),
            (Decimal("10"), Decimal("10")),
            (Decimal("20"), Decimal("20")),
            (Decimal("40"), Decimal("40")),
        ],
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        allocation=allocation,
        lower_bound=Decimal("-100"),
        upper_bound=Decimal("200"),
    )

    assert best_envy == Decimal("-100")
    assert best_premiums == (
        Premiums(
            room_1=Decimal("0"),
            room_2=Decimal("0"),
            room_3=Decimal("0"),
        ),
        Premiums(
            room_1=Decimal("10"),
            room_2=Decimal("10"),
            room_3=Decimal("-20"),
        ),
        Premiums(
            room_1=Decimal("20"),
            room_2=Decimal("20"),
            room_3=Decimal("-40"),
        ),
    )


def test_fine_candidates_searches_one_coarse_step_around_optimum() -> None:
    coarse_optima = (
        Premiums(
            room_1=Decimal("0"),
            room_2=Decimal("0"),
            room_3=Decimal("0"),
        ),
    )

    candidates = search._fine_candidates(
        coarse_optima=coarse_optima,
        lower_bound=Decimal("-100"),
        upper_bound=Decimal("200"),
    )

    assert (Decimal("-10"), Decimal("-10")) in candidates
    assert (Decimal("0"), Decimal("0")) in candidates
    assert (Decimal("10"), Decimal("10")) in candidates
    assert (Decimal("-11"), Decimal("0")) not in candidates
    assert (Decimal("11"), Decimal("0")) not in candidates


def test_fine_candidates_uses_one_pound_grid() -> None:
    coarse_optima = (
        Premiums(
            room_1=Decimal("0"),
            room_2=Decimal("0"),
            room_3=Decimal("0"),
        ),
    )

    candidates = search._fine_candidates(
        coarse_optima=coarse_optima,
        lower_bound=Decimal("-100"),
        upper_bound=Decimal("200"),
    )

    assert (Decimal("1"), Decimal("0")) in candidates
    assert (Decimal("-1"), Decimal("0")) in candidates
    assert (Decimal("0"), Decimal("1")) in candidates
    assert (Decimal("0"), Decimal("-1")) in candidates


def test_fine_candidates_takes_union_around_multiple_coarse_optima() -> None:
    coarse_optima = (
        Premiums(
            room_1=Decimal("0"),
            room_2=Decimal("0"),
            room_3=Decimal("0"),
        ),
        Premiums(
            room_1=Decimal("10"),
            room_2=Decimal("-10"),
            room_3=Decimal("0"),
        ),
    )

    candidates = search._fine_candidates(
        coarse_optima=coarse_optima,
        lower_bound=Decimal("-20"),
        upper_bound=Decimal("20"),
    )

    assert (Decimal("-10"), Decimal("10")) in candidates
    assert (Decimal("20"), Decimal("-20")) in candidates
    assert len(candidates) == 761


def test_fine_candidates_respects_search_bounds() -> None:
    coarse_optima = (
        Premiums(
            room_1=Decimal("-100"),
            room_2=Decimal("0"),
            room_3=Decimal("100"),
        ),
    )

    candidates = search._fine_candidates(
        coarse_optima=coarse_optima,
        lower_bound=Decimal("-100"),
        upper_bound=Decimal("200"),
    )

    room_1_values = {room_1 for room_1, _ in candidates}

    assert min(room_1_values) == Decimal("-100")
    assert max(room_1_values) == Decimal("-90")


def test_distance_squared_is_zero_for_identical_premiums() -> None:
    premiums = Premiums(
        room_1=Decimal("10"),
        room_2=Decimal("-5"),
        room_3=Decimal("-5"),
    )

    result = search._distance_squared(premiums, premiums)

    assert result == Decimal("0")


def test_distance_squared_uses_all_three_rooms() -> None:
    first = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    second = Premiums(
        room_1=Decimal("2"),
        room_2=Decimal("-1"),
        room_3=Decimal("-1"),
    )

    result = search._distance_squared(first, second)

    assert result == Decimal("6")


def test_midpoint_returns_midpoint_of_two_premium_splits() -> None:
    first = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    second = Premiums(
        room_1=Decimal("10"),
        room_2=Decimal("-4"),
        room_3=Decimal("-6"),
    )

    result = search._midpoint(first, second)

    assert result == Premiums(
        room_1=Decimal("5"),
        room_2=Decimal("-2"),
        room_3=Decimal("-3"),
    )


def test_midpoint_can_produce_fifty_pence_values() -> None:
    first = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    second = Premiums(
        room_1=Decimal("1"),
        room_2=Decimal("-1"),
        room_3=Decimal("0"),
    )

    result = search._midpoint(first, second)

    assert result == Premiums(
        room_1=Decimal("0.5"),
        room_2=Decimal("-0.5"),
        room_3=Decimal("0"),
    )


def test_midpoint_preserves_zero_sum_constraint() -> None:
    first = Premiums(
        room_1=Decimal("-17"),
        room_2=Decimal("9"),
        room_3=Decimal("8"),
    )
    second = Premiums(
        room_1=Decimal("4"),
        room_2=Decimal("-2"),
        room_3=Decimal("-2"),
    )

    result = search._midpoint(first, second)

    assert result.room_1 + result.room_2 + result.room_3 == Decimal("0")


def test_representative_optimum_returns_single_optimum_unchanged() -> None:
    optimum = Premiums(
        room_1=Decimal("13"),
        room_2=Decimal("-4"),
        room_3=Decimal("-9"),
    )

    result = search._representative_optimum((optimum,))

    assert result == optimum


def test_representative_optimum_uses_midpoint_of_furthest_optima() -> None:
    _, _, _, result = _test_example_2()

    assert result == Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("-1"),
        room_3=Decimal("1"),
    )


def test_representative_optimum_is_independent_of_input_order() -> None:
    first, middle, last, forward = _test_example_2()
    reverse = search._representative_optimum(
        (
            last,
            middle,
            first,
        )
    )

    assert forward == reverse


def test_representative_optimum_rejects_empty_collection() -> None:
    with pytest.raises(ValueError, match="At least one optimum is required"):
        search._representative_optimum(())


def test_search_allocation_finds_exact_integer_optimum_after_fine_search() -> None:
    subjective_premiums, _, result = _test_example_3()

    assert result.premiums == subjective_premiums
    assert result.maximum_envy == Decimal("0")


def test_search_allocation_refines_beyond_ten_pound_coarse_grid() -> None:
    _, _, result = _test_example_3()

    assert result.premiums.room_1 % Decimal("10") != Decimal("0")
    assert result.premiums.room_2 % Decimal("10") != Decimal("0")
    assert result.premiums == Premiums(
        room_1=Decimal("13"),
        room_2=Decimal("-4"),
        room_3=Decimal("-9"),
    )


def test_search_allocation_can_select_half_pound_midpoint() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("0.5"),
        room_2=Decimal("-0.5"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = search.search_allocation(
        friend_1_premiums=subjective_premiums,
        friend_2_premiums=subjective_premiums,
        friend_3_premiums=subjective_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    assert result.premiums == Premiums(
        room_1=Decimal("0.5"),
        room_2=Decimal("-0.5"),
        room_3=Decimal("0"),
    )
    assert result.maximum_envy == Decimal("0")


def test_search_allocation_uses_midpoint_of_optimal_continuum() -> None:
    friend_1_premiums, friend_2_premiums, friend_3_premiums, allocation = _test_example_1()

    result = search.search_allocation(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    assert result.premiums == Premiums(
        room_1=Decimal("16.5"),
        room_2=Decimal("16.5"),
        room_3=Decimal("-33"),
    )
    assert result.maximum_envy == Decimal("-100")


def test_search_allocation_respects_premium_bounds() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("250"),
        room_2=Decimal("-125"),
        room_3=Decimal("-125"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = search.search_allocation(
        friend_1_premiums=subjective_premiums,
        friend_2_premiums=subjective_premiums,
        friend_3_premiums=subjective_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    assert result.premiums == Premiums(
        room_1=Decimal("200"),
        room_2=Decimal("-100"),
        room_3=Decimal("-100"),
    )
    assert result.maximum_envy == Decimal("75")


def test_search_allocation_never_returns_negative_room_rent() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("250"),
        room_2=Decimal("-125"),
        room_3=Decimal("-125"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )
    rent = Decimal("300")

    result = search.search_allocation(
        friend_1_premiums=subjective_premiums,
        friend_2_premiums=subjective_premiums,
        friend_3_premiums=subjective_premiums,
        allocation=allocation,
        rent=rent,
    )

    base_share = rent / Decimal("3")
    room_rents = (
        base_share + result.premiums.room_1,
        base_share + result.premiums.room_2,
        base_share + result.premiums.room_3,
    )

    assert all(room_rent >= Decimal("0") for room_rent in room_rents)


def test_search_allocation_returned_premiums_sum_to_zero() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("37"),
        room_2=Decimal("-11"),
        room_3=Decimal("-26"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = search.search_allocation(
        friend_1_premiums=subjective_premiums,
        friend_2_premiums=subjective_premiums,
        friend_3_premiums=subjective_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    assert result.premiums.room_1 + result.premiums.room_2 + result.premiums.room_3 == Decimal("0")


def test_search_allocation_returns_same_allocation_it_was_given() -> None:
    subjective_premiums = Premiums(
        room_1=Decimal("20"),
        room_2=Decimal("0"),
        room_3=Decimal("-20"),
    )
    allocation = Allocation(
        friend_1=2,
        friend_2=3,
        friend_3=1,
    )

    result = search.search_allocation(
        friend_1_premiums=subjective_premiums,
        friend_2_premiums=subjective_premiums,
        friend_3_premiums=subjective_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    assert result.allocation == allocation


def test_search_allocation_reports_envy_for_returned_premiums() -> None:
    friend_1_premiums = Premiums(
        room_1=Decimal("80"),
        room_2=Decimal("-10"),
        room_3=Decimal("-70"),
    )
    friend_2_premiums = Premiums(
        room_1=Decimal("-40"),
        room_2=Decimal("90"),
        room_3=Decimal("-50"),
    )
    friend_3_premiums = Premiums(
        room_1=Decimal("-30"),
        room_2=Decimal("-60"),
        room_3=Decimal("90"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    result = search.search_allocation(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        allocation=allocation,
        rent=Decimal("300"),
    )

    independently_calculated_envy = maximum_envy(
        friend_1_premiums=friend_1_premiums,
        friend_2_premiums=friend_2_premiums,
        friend_3_premiums=friend_3_premiums,
        actual_premiums=result.premiums,
        allocation=allocation,
    )

    assert result.maximum_envy == independently_calculated_envy


@pytest.mark.parametrize(
    "rent",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("-300"),
    ],
)
def test_search_allocation_rejects_non_positive_rent(rent: Decimal) -> None:
    zero_premiums = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )
    allocation = Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )

    with pytest.raises(ValueError, match="Rent must be greater than zero"):
        search.search_allocation(
            friend_1_premiums=zero_premiums,
            friend_2_premiums=zero_premiums,
            friend_3_premiums=zero_premiums,
            allocation=allocation,
            rent=rent,
        )
