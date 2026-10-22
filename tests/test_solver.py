from decimal import Decimal

import pytest

from rent_envy_minimizer import solver
from rent_envy_minimizer.models import (
    Allocation,
    AllocationResult,
    Premiums,
    SolverResult,
    Valuation,
)


def _valuation_example_1() -> Valuation:
    return Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )


def _valuation_example_2() -> Valuation:
    return Valuation(
        room_1=Decimal("900"),
        room_2=Decimal("1200"),
        room_3=Decimal("900"),
    )


def _valuation_example_3() -> Valuation:
    return Valuation(
        room_1=Decimal("800"),
        room_2=Decimal("900"),
        room_3=Decimal("1300"),
    )


def _zero_premiums() -> Premiums:
    return Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("0"),
        room_3=Decimal("0"),
    )


def _allocation_result(
    *,
    friend_1: int,
    friend_2: int,
    friend_3: int,
    maximum_envy: Decimal,
) -> AllocationResult:
    return AllocationResult(
        allocation=Allocation(
            friend_1=friend_1,
            friend_2=friend_2,
            friend_3=friend_3,
        ),
        premiums=_zero_premiums(),
        maximum_envy=maximum_envy,
    )


def _make_fake_search_allocation(
    envy_by_allocation: dict[tuple[int, int, int], Decimal],
    *,
    premiums_by_allocation: dict[tuple[int, int, int], Premiums] | None = None,
):
    def fake_search_allocation(
        *,
        allocation: Allocation,
        **_: object,
    ) -> AllocationResult:
        key = (
            allocation.friend_1,
            allocation.friend_2,
            allocation.friend_3,
        )

        premiums = (
            premiums_by_allocation[key] if premiums_by_allocation is not None else _zero_premiums()
        )

        return AllocationResult(
            allocation=allocation,
            premiums=premiums,
            maximum_envy=envy_by_allocation[key],
        )

    return fake_search_allocation


def _test_example_1(
    monkeypatch: pytest.MonkeyPatch,
) -> SolverResult:
    def fake_search_allocation(
        *,
        allocation: Allocation,
        **_: object,
    ) -> AllocationResult:
        return AllocationResult(
            allocation=allocation,
            premiums=_zero_premiums(),
            maximum_envy=Decimal("0"),
        )

    monkeypatch.setattr(
        solver,
        "search_allocation",
        fake_search_allocation,
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    return result


def test_all_allocations_returns_exactly_six_allocations() -> None:
    allocations = solver._all_allocations()

    assert len(allocations) == 6


def test_all_allocations_contains_every_possible_room_assignment() -> None:
    allocations = solver._all_allocations()

    assert allocations == (
        Allocation(friend_1=1, friend_2=2, friend_3=3),
        Allocation(friend_1=1, friend_2=3, friend_3=2),
        Allocation(friend_1=2, friend_2=1, friend_3=3),
        Allocation(friend_1=2, friend_2=3, friend_3=1),
        Allocation(friend_1=3, friend_2=1, friend_3=2),
        Allocation(friend_1=3, friend_2=2, friend_3=1),
    )


def test_all_allocations_contains_no_duplicates() -> None:
    allocations = solver._all_allocations()

    assert len(set(allocations)) == 6


def test_all_allocations_assigns_each_room_exactly_once() -> None:
    for allocation in solver._all_allocations():
        assigned_rooms = {
            allocation.friend_1,
            allocation.friend_2,
            allocation.friend_3,
        }

        assert assigned_rooms == {1, 2, 3}


@pytest.mark.parametrize(
    ("allocation", "expected"),
    [
        (
            Allocation(friend_1=1, friend_2=2, friend_3=3),
            (1, 2, 3),
        ),
        (
            Allocation(friend_1=1, friend_2=3, friend_3=2),
            (1, 3, 2),
        ),
        (
            Allocation(friend_1=2, friend_2=1, friend_3=3),
            (2, 1, 3),
        ),
        (
            Allocation(friend_1=3, friend_2=2, friend_3=1),
            (3, 2, 1),
        ),
    ],
)
def test_allocation_sort_key_matches_friend_room_order(
    allocation: Allocation,
    expected: tuple[int, int, int],
) -> None:
    result = AllocationResult(
        allocation=allocation,
        premiums=_zero_premiums(),
        maximum_envy=Decimal("0"),
    )

    assert solver._allocation_sort_key(result) == expected


def test_solver_result_has_tie_is_false_with_one_best_result() -> None:
    best = _allocation_result(
        friend_1=1,
        friend_2=2,
        friend_3=3,
        maximum_envy=Decimal("-10"),
    )

    result = SolverResult(
        recommended=best,
        allocation_results=(best,),
        tied_best_results=(best,),
    )

    assert result.has_tie is False


def test_solver_result_has_tie_is_true_with_multiple_best_results() -> None:
    first = _allocation_result(
        friend_1=1,
        friend_2=2,
        friend_3=3,
        maximum_envy=Decimal("-10"),
    )
    second = _allocation_result(
        friend_1=1,
        friend_2=3,
        friend_3=2,
        maximum_envy=Decimal("-10"),
    )

    result = SolverResult(
        recommended=first,
        allocation_results=(first, second),
        tied_best_results=(first, second),
    )

    assert result.has_tie is True


def test_solve_converts_each_friends_valuation_to_premiums(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    friend_1_valuation = _valuation_example_1()
    friend_2_valuation = _valuation_example_2()
    friend_3_valuation = _valuation_example_3()

    friend_1_prem = Premiums(
        room_1=Decimal("1"),
        room_2=Decimal("0"),
        room_3=Decimal("-1"),
    )
    friend_2_prem = Premiums(
        room_1=Decimal("-1"),
        room_2=Decimal("1"),
        room_3=Decimal("0"),
    )
    friend_3_prem = Premiums(
        room_1=Decimal("0"),
        room_2=Decimal("-1"),
        room_3=Decimal("1"),
    )

    conversions = {
        friend_1_valuation: friend_1_prem,
        friend_2_valuation: friend_2_prem,
        friend_3_valuation: friend_3_prem,
    }
    converted_valuations: list[Valuation] = []

    def fake_valuation_to_premiums(valuation: Valuation) -> Premiums:
        converted_valuations.append(valuation)
        return conversions[valuation]

    def fake_search_allocation(
        *,
        friend_1_premiums: Premiums,
        friend_2_premiums: Premiums,
        friend_3_premiums: Premiums,
        allocation: Allocation,
        rent: Decimal,
    ) -> AllocationResult:
        assert friend_1_premiums == conversions[friend_1_valuation]
        assert friend_2_premiums == conversions[friend_2_valuation]
        assert friend_3_premiums == conversions[friend_3_valuation]
        assert rent == Decimal("3000")

        return AllocationResult(
            allocation=allocation,
            premiums=_zero_premiums(),
            maximum_envy=Decimal("0"),
        )

    monkeypatch.setattr(
        solver,
        "valuation_to_premiums",
        fake_valuation_to_premiums,
    )
    monkeypatch.setattr(
        solver,
        "search_allocation",
        fake_search_allocation,
    )

    solver.solve(
        friend_1_valuation=friend_1_valuation,
        friend_2_valuation=friend_2_valuation,
        friend_3_valuation=friend_3_valuation,
        rent=Decimal("3000"),
    )

    assert converted_valuations == [
        friend_1_valuation,
        friend_2_valuation,
        friend_3_valuation,
    ]


def test_solve_searches_all_six_allocations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    searched_allocations: list[Allocation] = []

    def fake_search_allocation(
        *,
        allocation: Allocation,
        **_: object,
    ) -> AllocationResult:
        searched_allocations.append(allocation)

        return AllocationResult(
            allocation=allocation,
            premiums=_zero_premiums(),
            maximum_envy=Decimal("0"),
        )

    monkeypatch.setattr(
        solver,
        "search_allocation",
        fake_search_allocation,
    )

    solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert tuple(searched_allocations) == solver._all_allocations()


def test_solve_passes_final_rent_to_every_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rents_seen: list[Decimal] = []

    def fake_search_allocation(
        *,
        allocation: Allocation,
        rent: Decimal,
        **_: object,
    ) -> AllocationResult:
        rents_seen.append(rent)

        return AllocationResult(
            allocation=allocation,
            premiums=_zero_premiums(),
            maximum_envy=Decimal("0"),
        )

    monkeypatch.setattr(
        solver,
        "search_allocation",
        fake_search_allocation,
    )

    solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("2745"),
    )

    assert rents_seen == [Decimal("2745")] * 6


def test_solve_returns_all_six_allocation_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("10"),
        (1, 3, 2): Decimal("20"),
        (2, 1, 3): Decimal("30"),
        (2, 3, 1): Decimal("40"),
        (3, 1, 2): Decimal("50"),
        (3, 2, 1): Decimal("60"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert len(result.allocation_results) == 6
    assert (
        tuple(allocation_result.allocation for allocation_result in result.allocation_results)
        == solver._all_allocations()
    )


def test_solve_selects_allocation_with_lowest_positive_maximum_envy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("75"),
        (1, 3, 2): Decimal("40"),
        (2, 1, 3): Decimal("20"),
        (2, 3, 1): Decimal("55"),
        (3, 1, 2): Decimal("35"),
        (3, 2, 1): Decimal("60"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.recommended.allocation == Allocation(
        friend_1=2,
        friend_2=1,
        friend_3=3,
    )
    assert result.recommended.maximum_envy == Decimal("20")


def test_solve_prefers_zero_envy_over_positive_envy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("50"),
        (1, 3, 2): Decimal("10"),
        (2, 1, 3): Decimal("0"),
        (2, 3, 1): Decimal("20"),
        (3, 1, 2): Decimal("5"),
        (3, 2, 1): Decimal("15"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.recommended.maximum_envy == Decimal("0")
    assert result.recommended.allocation == Allocation(
        friend_1=2,
        friend_2=1,
        friend_3=3,
    )


def test_solve_prefers_negative_envy_over_zero_envy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("0"),
        (1, 3, 2): Decimal("-5"),
        (2, 1, 3): Decimal("10"),
        (2, 3, 1): Decimal("20"),
        (3, 1, 2): Decimal("5"),
        (3, 2, 1): Decimal("15"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.recommended.maximum_envy == Decimal("-5")
    assert result.recommended.allocation == Allocation(
        friend_1=1,
        friend_2=3,
        friend_3=2,
    )


def test_solve_prefers_more_negative_maximum_envy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("-10"),
        (1, 3, 2): Decimal("-15"),
        (2, 1, 3): Decimal("-25"),
        (2, 3, 1): Decimal("-5"),
        (3, 1, 2): Decimal("0"),
        (3, 2, 1): Decimal("10"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.recommended.maximum_envy == Decimal("-25")
    assert result.recommended.allocation == Allocation(
        friend_1=2,
        friend_2=1,
        friend_3=3,
    )


def test_solve_retains_all_tied_best_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("-10"),
        (1, 3, 2): Decimal("-20"),
        (2, 1, 3): Decimal("-20"),
        (2, 3, 1): Decimal("0"),
        (3, 1, 2): Decimal("10"),
        (3, 2, 1): Decimal("20"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.has_tie is True
    assert tuple(tied_result.allocation for tied_result in result.tied_best_results) == (
        Allocation(friend_1=1, friend_2=3, friend_3=2),
        Allocation(friend_1=2, friend_2=1, friend_3=3),
    )


def test_solve_applies_lexicographic_tie_break(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("10"),
        (1, 3, 2): Decimal("-20"),
        (2, 1, 3): Decimal("-20"),
        (2, 3, 1): Decimal("-20"),
        (3, 1, 2): Decimal("0"),
        (3, 2, 1): Decimal("5"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.has_tie is True
    assert result.recommended.allocation == Allocation(
        friend_1=1,
        friend_2=3,
        friend_3=2,
    )


def test_solve_recommended_result_is_member_of_allocation_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_search_allocation(
        *,
        allocation: Allocation,
        **_: object,
    ) -> AllocationResult:
        maximum_envy = Decimal(str(allocation.friend_1))

        return AllocationResult(
            allocation=allocation,
            premiums=_zero_premiums(),
            maximum_envy=maximum_envy,
        )

    monkeypatch.setattr(
        solver,
        "search_allocation",
        fake_search_allocation,
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.recommended in result.allocation_results


def test_solve_recommended_result_is_member_of_tied_best_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _test_example_1(monkeypatch)

    assert result.recommended in result.tied_best_results


def test_solve_with_all_allocations_tied_selects_identity_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _test_example_1(monkeypatch)

    assert len(result.tied_best_results) == 6
    assert result.recommended.allocation == Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )


def test_solve_has_no_tie_when_only_one_allocation_is_best(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envy_by_allocation = {
        (1, 2, 3): Decimal("0"),
        (1, 3, 2): Decimal("10"),
        (2, 1, 3): Decimal("20"),
        (2, 3, 1): Decimal("30"),
        (3, 1, 2): Decimal("40"),
        (3, 2, 1): Decimal("50"),
    }

    monkeypatch.setattr(
        solver,
        "search_allocation",
        _make_fake_search_allocation(envy_by_allocation),
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.has_tie is False
    assert len(result.tied_best_results) == 1
    assert result.tied_best_results[0] == result.recommended


def test_solve_preserves_premiums_returned_by_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_premiums = Premiums(
        room_1=Decimal("125"),
        room_2=Decimal("-25"),
        room_3=Decimal("-100"),
    )

    def fake_search_allocation(
        *,
        allocation: Allocation,
        **_: object,
    ) -> AllocationResult:
        maximum_envy = (
            Decimal("-10")
            if allocation
            == Allocation(
                friend_1=2,
                friend_2=1,
                friend_3=3,
            )
            else Decimal("10")
        )

        premiums = expected_premiums if maximum_envy == Decimal("-10") else _zero_premiums()

        return AllocationResult(
            allocation=allocation,
            premiums=premiums,
            maximum_envy=maximum_envy,
        )

    monkeypatch.setattr(
        solver,
        "search_allocation",
        fake_search_allocation,
    )

    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert result.recommended.premiums == expected_premiums


def test_solve_integration_finds_natural_distinct_room_allocation() -> None:
    friend_1_valuation = Valuation(
        room_1=Decimal("1300"),
        room_2=Decimal("1000"),
        room_3=Decimal("700"),
    )
    friend_2_valuation = Valuation(
        room_1=Decimal("800"),
        room_2=Decimal("1400"),
        room_3=Decimal("800"),
    )
    friend_3_valuation = Valuation(
        room_1=Decimal("700"),
        room_2=Decimal("900"),
        room_3=Decimal("1400"),
    )

    result = solver.solve(
        friend_1_valuation=friend_1_valuation,
        friend_2_valuation=friend_2_valuation,
        friend_3_valuation=friend_3_valuation,
        rent=Decimal("3000"),
    )

    assert result.recommended.allocation == Allocation(
        friend_1=1,
        friend_2=2,
        friend_3=3,
    )
    assert result.recommended.maximum_envy < Decimal("0")


def test_solve_integration_returns_six_results() -> None:
    result = solver.solve(
        friend_1_valuation=_valuation_example_1(),
        friend_2_valuation=_valuation_example_2(),
        friend_3_valuation=_valuation_example_3(),
        rent=Decimal("3000"),
    )

    assert len(result.allocation_results) == 6
    assert {allocation_result.allocation for allocation_result in result.allocation_results} == set(
        solver._all_allocations()
    )
