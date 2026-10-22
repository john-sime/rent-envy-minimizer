import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from rent_envy_minimizer.models import AllocationResult, SolverResult, Valuation
from rent_envy_minimizer.solver import solve

INPUTS_DIRECTORY = Path("inputs")
EXPECTED_FRIENDS = ("friend_1", "friend_2", "friend_3")
EXPECTED_ROOMS = ("room_1", "room_2", "room_3")


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rent-envy",
        description="Find a room allocation and rent split that minimises maximum envy.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    solve_parser = subparsers.add_parser(
        "solve",
        help="Solve a three-person rent allocation.",
    )
    solve_parser.add_argument(
        "input_file",
        help="JSON filename located in the inputs/ directory.",
    )
    solve_parser.add_argument(
        "--rent",
        required=True,
        help="Final negotiated monthly rent for the property.",
    )

    return parser.parse_args()


def _resolve_input_path(filename: str) -> Path:
    """
    Resolve an input filename inside the repository's inputs directory.

    Input files are intentionally restricted to the inputs/ directory so the
    CLI has one predictable location for valuation files.
    """
    supplied = Path(filename)

    if supplied.name != filename:
        raise ValueError(
            "Provide only the JSON filename, not a path. "
            "Valuation files belong in the inputs/ folder."
        )

    if supplied.suffix.lower() != ".json":
        raise ValueError("Input file must have a .json extension.")

    path = INPUTS_DIRECTORY / supplied

    if not path.is_file():
        raise FileNotFoundError(path)

    return path


def _load_json(path: Path) -> dict[str, Any]:
    """Load and validate the top-level JSON structure."""
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ValueError("Input JSON must contain an object at the top level.")

    return data


def _to_decimal(value: Any, *, field: str) -> Decimal:
    """Convert a JSON value to Decimal without introducing float error."""
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a numeric value.")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a valid numeric value.") from exc

    if not result.is_finite():
        raise ValueError(f"{field} must be a finite numeric value.")

    return result


def _parse_valuation(
    data: dict[str, Any],
    *,
    friend: str,
) -> Valuation:
    """Parse one friend's three room valuations."""
    if friend not in data:
        raise ValueError(f"Missing required friend: {friend}.")

    friend_data = data[friend]

    if not isinstance(friend_data, dict):
        raise ValueError(f"{friend} must contain an object of room valuations.")

    missing_rooms = [room for room in EXPECTED_ROOMS if room not in friend_data]

    if missing_rooms:
        missing = ", ".join(missing_rooms)
        raise ValueError(f"{friend} is missing required room valuation(s): {missing}.")

    return Valuation(
        room_1=_to_decimal(
            friend_data["room_1"],
            field=f"{friend}.room_1",
        ),
        room_2=_to_decimal(
            friend_data["room_2"],
            field=f"{friend}.room_2",
        ),
        room_3=_to_decimal(
            friend_data["room_3"],
            field=f"{friend}.room_3",
        ),
    )


def _parse_valuations(
    data: dict[str, Any],
) -> tuple[Valuation, Valuation, Valuation]:
    """Parse all three friends' valuations."""
    unexpected_friends = set(data) - set(EXPECTED_FRIENDS)

    if unexpected_friends:
        unexpected = ", ".join(sorted(unexpected_friends))
        raise ValueError(f"Unexpected top-level field(s): {unexpected}.")

    return (
        _parse_valuation(data, friend="friend_1"),
        _parse_valuation(data, friend="friend_2"),
        _parse_valuation(data, friend="friend_3"),
    )


def _parse_rent(raw_rent: str) -> Decimal:
    """Parse and validate the final negotiated rent."""
    try:
        rent = Decimal(raw_rent)
    except InvalidOperation as exc:
        raise ValueError("Rent must be a valid numeric value.") from exc

    if not rent.is_finite():
        raise ValueError("Rent must be a finite numeric value.")

    if rent <= Decimal("0"):
        raise ValueError("Rent must be greater than zero.")

    return rent


def _format_money(value: Decimal, *, signed: bool = False) -> str:
    """Format a Decimal as a pound-denominated monetary value."""
    quantized = value.quantize(Decimal("0.01"))

    if signed:
        if quantized > Decimal("0"):
            return f"+£{quantized:,.2f}"
        if quantized < Decimal("0"):
            return f"-£{abs(quantized):,.2f}"

    return f"£{quantized:,.2f}"


def _allocation_description(result: AllocationResult) -> str:
    """Return a compact friend-to-room allocation description."""
    allocation = result.allocation

    return (
        f"friend_1 -> room_{allocation.friend_1}, "
        f"friend_2 -> room_{allocation.friend_2}, "
        f"friend_3 -> room_{allocation.friend_3}"
    )


def _room_rents(
    *,
    rent: Decimal,
    result: AllocationResult,
) -> tuple[Decimal, Decimal, Decimal]:
    """Convert room premiums into final room rents."""
    base_share = rent / Decimal("3")

    room_1 = base_share + result.premiums.room_1
    room_2 = base_share + result.premiums.room_2

    # Derive the final room from the total so that the three room rents
    # preserve the negotiated total exactly despite Decimal thirds.
    room_3 = rent - room_1 - room_2

    return room_1, room_2, room_3


def _print_recommended_result(
    *,
    result: SolverResult,
    rent: Decimal,
) -> None:
    """Print the recommended allocation and final room rents."""
    recommended = result.recommended
    room_1_rent, room_2_rent, room_3_rent = _room_rents(
        rent=rent,
        result=recommended,
    )

    print()
    print("RECOMMENDED ALLOCATION")
    print("----------------------")
    print(f"friend_1 -> room_{recommended.allocation.friend_1}")
    print(f"friend_2 -> room_{recommended.allocation.friend_2}")
    print(f"friend_3 -> room_{recommended.allocation.friend_3}")

    print()
    print("ROOM RENTS")
    print("----------")
    print(f"room_1: {_format_money(room_1_rent)}")
    print(f"room_2: {_format_money(room_2_rent)}")
    print(f"room_3: {_format_money(room_3_rent)}")

    print()
    print("PREMIUMS / DISCOUNTS")
    print("--------------------")
    print(f"room_1: {_format_money(recommended.premiums.room_1, signed=True)}")
    print(f"room_2: {_format_money(recommended.premiums.room_2, signed=True)}")
    print(f"room_3: {_format_money(recommended.premiums.room_3, signed=True)}")

    print()
    print("MAXIMUM ENVY")
    print("------------")
    print(_format_money(recommended.maximum_envy, signed=True))

    if recommended.maximum_envy < Decimal("0"):
        print("Result: STRICTLY ENVY FREE")
    elif recommended.maximum_envy == Decimal("0"):
        print("Result: ENVY FREE")
    else:
        print("Result: ENVY REMAINS")

    if result.has_tie:
        print()
        print("WARNING")
        print("-------")
        print(
            f"{len(result.tied_best_results)} allocations achieved the "
            "same best maximum-envy score."
        )
        print(
            "The recommended allocation was selected using the deterministic "
            "lower-index tie-break rule."
        )


def _print_all_results(result: SolverResult) -> None:
    """Print the optimal premium split for all six room allocations."""
    print()
    print("ALL ALLOCATIONS")
    print("---------------")

    for index, allocation_result in enumerate(
        result.allocation_results,
        start=1,
    ):
        marker = "  < RECOMMENDED" if allocation_result == result.recommended else ""

        print()
        print(f"{index}. {_allocation_description(allocation_result)}{marker}")
        print(
            "   premiums: "
            f"room_1 {_format_money(allocation_result.premiums.room_1, signed=True)}, "
            f"room_2 {_format_money(allocation_result.premiums.room_2, signed=True)}, "
            f"room_3 {_format_money(allocation_result.premiums.room_3, signed=True)}"
        )
        print(f"   maximum envy: {_format_money(allocation_result.maximum_envy, signed=True)}")


def _run_solve(
    *,
    input_file: str,
    raw_rent: str,
) -> None:
    """Run the solve command."""
    input_path = _resolve_input_path(input_file)
    rent = _parse_rent(raw_rent)

    data = _load_json(input_path)

    (
        friend_1_valuation,
        friend_2_valuation,
        friend_3_valuation,
    ) = _parse_valuations(data)

    result = solve(
        friend_1_valuation=friend_1_valuation,
        friend_2_valuation=friend_2_valuation,
        friend_3_valuation=friend_3_valuation,
        rent=rent,
    )

    print(f"Input: {input_path}")
    print(f"Final negotiated rent: {_format_money(rent)}")

    _print_recommended_result(
        result=result,
        rent=rent,
    )
    _print_all_results(result)


def main() -> None:
    """CLI entry point."""
    args = _parse_arguments()

    try:
        if args.command == "solve":
            _run_solve(
                input_file=args.input_file,
                raw_rent=args.rent,
            )
    except FileNotFoundError as exc:
        path = exc.args[0]

        print(
            f"Input file not found: {path}",
            file=sys.stderr,
        )
        print(
            "\nPlace your valuation JSON file in the inputs/ folder and try again.",
            file=sys.stderr,
        )
        print(
            "For the expected format, see inputs/example.json.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    except ValueError as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
