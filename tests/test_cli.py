import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from rent_envy_minimizer import cli
from rent_envy_minimizer.models import (
    Allocation,
    AllocationResult,
    Premiums,
    SolverResult,
    Valuation,
)


def _allocation_result(
    *,
    friend_1: int = 1,
    friend_2: int = 2,
    friend_3: int = 3,
    room_1: str = "0",
    room_2: str = "0",
    room_3: str = "0",
    maximum_envy: str = "0",
) -> AllocationResult:
    return AllocationResult(
        allocation=Allocation(
            friend_1=friend_1,
            friend_2=friend_2,
            friend_3=friend_3,
        ),
        premiums=Premiums(
            room_1=Decimal(room_1),
            room_2=Decimal(room_2),
            room_3=Decimal(room_3),
        ),
        maximum_envy=Decimal(maximum_envy),
    )


def _solver_result(
    *,
    recommended: AllocationResult | None = None,
    tied_best_results: tuple[AllocationResult, ...] | None = None,
) -> SolverResult:
    if recommended is None:
        recommended = _allocation_result(
            room_1="100",
            room_2="-25",
            room_3="-75",
            maximum_envy="-10",
        )

    other_results = (
        _allocation_result(
            friend_1=1,
            friend_2=3,
            friend_3=2,
            maximum_envy="20",
        ),
        _allocation_result(
            friend_1=2,
            friend_2=1,
            friend_3=3,
            maximum_envy="30",
        ),
        _allocation_result(
            friend_1=2,
            friend_2=3,
            friend_3=1,
            maximum_envy="40",
        ),
        _allocation_result(
            friend_1=3,
            friend_2=1,
            friend_3=2,
            maximum_envy="50",
        ),
        _allocation_result(
            friend_1=3,
            friend_2=2,
            friend_3=1,
            maximum_envy="60",
        ),
    )

    if tied_best_results is None:
        tied_best_results = (recommended,)

    return SolverResult(
        recommended=recommended,
        allocation_results=(recommended, *other_results),
        tied_best_results=tied_best_results,
    )


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


def _valid_input_data() -> dict[str, dict[str, int]]:
    return {
        "friend_1": {
            "room_1": 1200,
            "room_2": 1000,
            "room_3": 800,
        },
        "friend_2": {
            "room_1": 900,
            "room_2": 1200,
            "room_3": 900,
        },
        "friend_3": {
            "room_1": 800,
            "room_2": 900,
            "room_3": 1300,
        },
    }


def test_resolve_input_path_finds_json_in_inputs_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs_directory = tmp_path / "inputs"
    inputs_directory.mkdir()
    input_file = inputs_directory / "property.json"
    input_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "INPUTS_DIRECTORY",
        inputs_directory,
    )

    result = cli._resolve_input_path("property.json")

    assert result == input_file


def test_resolve_input_path_rejects_path_instead_of_filename() -> None:
    with pytest.raises(
        ValueError,
        match="Provide only the JSON filename, not a path",
    ):
        cli._resolve_input_path("inputs/property.json")


def test_resolve_input_path_rejects_non_json_extension() -> None:
    with pytest.raises(
        ValueError,
        match="Input file must have a .json extension",
    ):
        cli._resolve_input_path("property.txt")


def test_resolve_input_path_accepts_uppercase_json_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs_directory = tmp_path / "inputs"
    inputs_directory.mkdir()
    input_file = inputs_directory / "property.JSON"
    input_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "INPUTS_DIRECTORY",
        inputs_directory,
    )

    result = cli._resolve_input_path("property.JSON")

    assert result == input_file


def test_resolve_input_path_raises_when_file_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs_directory = tmp_path / "inputs"
    inputs_directory.mkdir()

    monkeypatch.setattr(
        cli,
        "INPUTS_DIRECTORY",
        inputs_directory,
    )

    with pytest.raises(FileNotFoundError):
        cli._resolve_input_path("missing.json")


def test_load_json_returns_top_level_object(tmp_path: Path) -> None:
    path = tmp_path / "property.json"
    expected = _valid_input_data()
    _write_json(path, expected)

    result = cli._load_json(path)

    assert result == expected


def test_load_json_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "property.json"
    path.write_text(
        '{"friend_1": ',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSON",
    ):
        cli._load_json(path)


@pytest.mark.parametrize(
    "data",
    [
        [],
        [1, 2, 3],
        "text",
        123,
        None,
    ],
)
def test_load_json_rejects_non_object_top_level(
    tmp_path: Path,
    data: object,
) -> None:
    path = tmp_path / "property.json"
    _write_json(path, data)

    with pytest.raises(
        ValueError,
        match="Input JSON must contain an object at the top level",
    ):
        cli._load_json(path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1200, Decimal("1200")),
        (1200.5, Decimal("1200.5")),
        ("1200.50", Decimal("1200.50")),
        (-100, Decimal("-100")),
        (0, Decimal("0")),
    ],
)
def test_to_decimal_converts_numeric_values(
    value: object,
    expected: Decimal,
) -> None:
    result = cli._to_decimal(
        value,
        field="friend_1.room_1",
    )

    assert result == expected


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
    ],
)
def test_to_decimal_rejects_boolean_values(value: bool) -> None:
    with pytest.raises(
        ValueError,
        match="friend_1.room_1 must be a numeric value",
    ):
        cli._to_decimal(
            value,
            field="friend_1.room_1",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "hello",
        {},
        [],
    ],
)
def test_to_decimal_rejects_non_numeric_values(value: object) -> None:
    with pytest.raises(
        ValueError,
        match="friend_1.room_1 must be a valid numeric value",
    ):
        cli._to_decimal(
            value,
            field="friend_1.room_1",
        )


@pytest.mark.parametrize(
    "value",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_to_decimal_rejects_non_finite_values(value: str) -> None:
    with pytest.raises(
        ValueError,
        match="friend_1.room_1 must be a finite numeric value",
    ):
        cli._to_decimal(
            value,
            field="friend_1.room_1",
        )


def test_parse_valuation_creates_expected_model() -> None:
    data = _valid_input_data()

    result = cli._parse_valuation(
        data,
        friend="friend_1",
    )

    assert result == Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )


def test_parse_valuation_rejects_missing_friend() -> None:
    data = _valid_input_data()
    del data["friend_2"]

    with pytest.raises(
        ValueError,
        match="Missing required friend: friend_2",
    ):
        cli._parse_valuation(
            data,
            friend="friend_2",
        )


def test_parse_valuation_rejects_non_object_friend_data() -> None:
    data: dict[str, object] = {
        "friend_1": 1200,
    }

    with pytest.raises(
        ValueError,
        match="friend_1 must contain an object of room valuations",
    ):
        cli._parse_valuation(
            data,
            friend="friend_1",
        )


def test_parse_valuation_rejects_missing_room() -> None:
    data = _valid_input_data()
    del data["friend_1"]["room_2"]

    with pytest.raises(
        ValueError,
        match="friend_1 is missing required room valuation",
    ):
        cli._parse_valuation(
            data,
            friend="friend_1",
        )


def test_parse_valuation_reports_all_missing_rooms() -> None:
    data = _valid_input_data()
    del data["friend_1"]["room_1"]
    del data["friend_1"]["room_3"]

    with pytest.raises(ValueError) as exc_info:
        cli._parse_valuation(
            data,
            friend="friend_1",
        )

    message = str(exc_info.value)

    assert "room_1" in message
    assert "room_3" in message


def test_parse_valuations_returns_three_valuations() -> None:
    data = _valid_input_data()

    friend_1, friend_2, friend_3 = cli._parse_valuations(data)

    assert friend_1 == Valuation(
        room_1=Decimal("1200"),
        room_2=Decimal("1000"),
        room_3=Decimal("800"),
    )
    assert friend_2 == Valuation(
        room_1=Decimal("900"),
        room_2=Decimal("1200"),
        room_3=Decimal("900"),
    )
    assert friend_3 == Valuation(
        room_1=Decimal("800"),
        room_2=Decimal("900"),
        room_3=Decimal("1300"),
    )


def test_parse_valuations_rejects_unexpected_top_level_field() -> None:
    data = _valid_input_data()
    data["friend_4"] = {
        "room_1": 1000,
        "room_2": 1000,
        "room_3": 1000,
    }

    with pytest.raises(
        ValueError,
        match="Unexpected top-level field",
    ):
        cli._parse_valuations(data)


@pytest.mark.parametrize(
    ("raw_rent", "expected"),
    [
        ("2700", Decimal("2700")),
        ("2700.50", Decimal("2700.50")),
        ("1", Decimal("1")),
        ("0.01", Decimal("0.01")),
    ],
)
def test_parse_rent_accepts_positive_numbers(
    raw_rent: str,
    expected: Decimal,
) -> None:
    assert cli._parse_rent(raw_rent) == expected


@pytest.mark.parametrize(
    "raw_rent",
    [
        "0",
        "-1",
        "-2700",
    ],
)
def test_parse_rent_rejects_non_positive_values(raw_rent: str) -> None:
    with pytest.raises(
        ValueError,
        match="Rent must be greater than zero",
    ):
        cli._parse_rent(raw_rent)


@pytest.mark.parametrize(
    "raw_rent",
    [
        "hello",
        "",
    ],
)
def test_parse_rent_rejects_invalid_numbers(raw_rent: str) -> None:
    with pytest.raises(
        ValueError,
        match="Rent must be a valid numeric value",
    ):
        cli._parse_rent(raw_rent)


@pytest.mark.parametrize(
    "raw_rent",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_parse_rent_rejects_non_finite_values(raw_rent: str) -> None:
    with pytest.raises(
        ValueError,
        match="Rent must be a finite numeric value",
    ):
        cli._parse_rent(raw_rent)


@pytest.mark.parametrize(
    ("value", "signed", "expected"),
    [
        (Decimal("100"), False, "£100.00"),
        (Decimal("100"), True, "+£100.00"),
        (Decimal("-100"), False, "£-100.00"),
        (Decimal("-100"), True, "-£100.00"),
        (Decimal("0"), False, "£0.00"),
        (Decimal("0"), True, "£0.00"),
        (Decimal("0.5"), True, "+£0.50"),
        (Decimal("-0.5"), True, "-£0.50"),
        (Decimal("1234.5"), False, "£1,234.50"),
    ],
)
def test_format_money(
    value: Decimal,
    signed: bool,
    expected: str,
) -> None:
    assert (
        cli._format_money(
            value,
            signed=signed,
        )
        == expected
    )


def test_allocation_description_formats_all_three_friends() -> None:
    result = _allocation_result(
        friend_1=2,
        friend_2=3,
        friend_3=1,
    )

    description = cli._allocation_description(result)

    assert description == "friend_1 -> room_2, friend_2 -> room_3, friend_3 -> room_1"


def test_room_rents_applies_premiums_to_base_share() -> None:
    result = _allocation_result(
        room_1="150",
        room_2="-50",
        room_3="-100",
    )

    room_1, room_2, room_3 = cli._room_rents(
        rent=Decimal("2700"),
        result=result,
    )

    assert room_1 == Decimal("1050")
    assert room_2 == Decimal("850")
    assert room_3 == Decimal("800")


def test_room_rents_preserves_total_exactly_when_rent_has_repeating_third() -> None:
    result = _allocation_result(
        room_1="0",
        room_2="0",
        room_3="0",
    )

    room_1, room_2, room_3 = cli._room_rents(
        rent=Decimal("100"),
        result=result,
    )

    assert room_1 + room_2 + room_3 == Decimal("100")


def test_print_recommended_result_shows_negative_envy_as_strictly_envy_free(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _solver_result(
        recommended=_allocation_result(
            friend_1=2,
            friend_2=1,
            friend_3=3,
            room_1="150",
            room_2="-50",
            room_3="-100",
            maximum_envy="-18",
        )
    )

    cli._print_recommended_result(
        result=result,
        rent=Decimal("2700"),
    )

    output = capsys.readouterr().out

    assert "RECOMMENDED ALLOCATION" in output
    assert "friend_1 -> room_2" in output
    assert "friend_2 -> room_1" in output
    assert "friend_3 -> room_3" in output
    assert "room_1: £1,050.00" in output
    assert "room_2: £850.00" in output
    assert "room_3: £800.00" in output
    assert "-£18.00" in output
    assert "Result: STRICTLY ENVY FREE" in output


def test_print_recommended_result_shows_zero_envy_as_envy_free(
    capsys: pytest.CaptureFixture[str],
) -> None:
    recommended = _allocation_result(
        maximum_envy="0",
    )
    result = _solver_result(
        recommended=recommended,
    )

    cli._print_recommended_result(
        result=result,
        rent=Decimal("3000"),
    )

    output = capsys.readouterr().out

    assert "Result: ENVY FREE" in output
    assert "STRICTLY ENVY FREE" not in output


def test_print_recommended_result_reports_remaining_positive_envy(
    capsys: pytest.CaptureFixture[str],
) -> None:
    recommended = _allocation_result(
        maximum_envy="25",
    )
    result = _solver_result(
        recommended=recommended,
    )

    cli._print_recommended_result(
        result=result,
        rent=Decimal("3000"),
    )

    output = capsys.readouterr().out

    assert "Result: ENVY REMAINS" in output


def test_print_recommended_result_shows_tie_warning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    recommended = _allocation_result(
        maximum_envy="-10",
    )
    tied = _allocation_result(
        friend_1=1,
        friend_2=3,
        friend_3=2,
        maximum_envy="-10",
    )
    result = _solver_result(
        recommended=recommended,
        tied_best_results=(recommended, tied),
    )

    cli._print_recommended_result(
        result=result,
        rent=Decimal("3000"),
    )

    output = capsys.readouterr().out

    assert "WARNING" in output
    assert "2 allocations achieved the same best maximum-envy score" in output
    assert "lower-index tie-break rule" in output


def test_print_recommended_result_omits_tie_warning_when_unique(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _solver_result()

    cli._print_recommended_result(
        result=result,
        rent=Decimal("3000"),
    )

    output = capsys.readouterr().out

    assert "WARNING" not in output


def test_print_all_results_outputs_all_six_allocations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _solver_result()

    cli._print_all_results(result)

    output = capsys.readouterr().out

    assert "ALL ALLOCATIONS" in output

    for index in range(1, 7):
        assert f"{index}." in output


def test_print_all_results_marks_recommended_result(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _solver_result()

    cli._print_all_results(result)

    output = capsys.readouterr().out

    assert "< RECOMMENDED" in output


def test_run_solve_passes_parsed_values_to_solver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs_directory = tmp_path / "inputs"
    inputs_directory.mkdir()
    input_file = inputs_directory / "property.json"
    _write_json(
        input_file,
        _valid_input_data(),
    )

    monkeypatch.setattr(
        cli,
        "INPUTS_DIRECTORY",
        inputs_directory,
    )

    calls: list[
        tuple[
            Valuation,
            Valuation,
            Valuation,
            Decimal,
        ]
    ] = []

    expected_result = _solver_result()

    def fake_solve(
        *,
        friend_1_valuation: Valuation,
        friend_2_valuation: Valuation,
        friend_3_valuation: Valuation,
        rent: Decimal,
    ) -> SolverResult:
        calls.append(
            (
                friend_1_valuation,
                friend_2_valuation,
                friend_3_valuation,
                rent,
            )
        )
        return expected_result

    monkeypatch.setattr(
        cli,
        "solve",
        fake_solve,
    )

    cli._run_solve(
        input_file="property.json",
        raw_rent="2700",
    )

    assert calls == [
        (
            Valuation(
                room_1=Decimal("1200"),
                room_2=Decimal("1000"),
                room_3=Decimal("800"),
            ),
            Valuation(
                room_1=Decimal("900"),
                room_2=Decimal("1200"),
                room_3=Decimal("900"),
            ),
            Valuation(
                room_1=Decimal("800"),
                room_2=Decimal("900"),
                room_3=Decimal("1300"),
            ),
            Decimal("2700"),
        )
    ]

    output = capsys.readouterr().out

    assert f"Input: {input_file}" in output
    assert "Final negotiated rent: £2,700.00" in output


def test_run_solve_prints_recommended_and_allocation_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs_directory = tmp_path / "inputs"
    inputs_directory.mkdir()
    input_file = inputs_directory / "property.json"
    _write_json(
        input_file,
        _valid_input_data(),
    )

    monkeypatch.setattr(
        cli,
        "INPUTS_DIRECTORY",
        inputs_directory,
    )
    monkeypatch.setattr(
        cli,
        "solve",
        lambda **_: _solver_result(),
    )

    cli._run_solve(
        input_file="property.json",
        raw_rent="2700",
    )

    output = capsys.readouterr().out

    assert "RECOMMENDED ALLOCATION" in output
    assert "ROOM RENTS" in output
    assert "PREMIUMS / DISCOUNTS" in output
    assert "MAXIMUM ENVY" in output
    assert "ALL ALLOCATIONS" in output


def test_main_runs_solve_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run_solve(
        *,
        input_file: str,
        raw_rent: str,
    ) -> None:
        calls.append(
            (
                input_file,
                raw_rent,
            )
        )

    monkeypatch.setattr(
        cli,
        "_run_solve",
        fake_run_solve,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rent-envy",
            "solve",
            "property.json",
            "--rent",
            "2700",
        ],
    )

    cli.main()

    assert calls == [
        (
            "property.json",
            "2700",
        )
    ]


def test_main_missing_file_exits_with_code_two_and_helpful_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_path = Path("inputs") / "missing.json"

    def fake_run_solve(**_: object) -> None:
        raise FileNotFoundError(missing_path)

    monkeypatch.setattr(
        cli,
        "_run_solve",
        fake_run_solve,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rent-envy",
            "solve",
            "missing.json",
            "--rent",
            "2700",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "Input file not found" in captured.err
    assert "missing.json" in captured.err
    assert "Place your valuation JSON file in the inputs/ folder" in captured.err
    assert "inputs/example.json" in captured.err


def test_main_invalid_input_exits_with_code_two(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_solve(**_: object) -> None:
        raise ValueError("Example validation failure.")

    monkeypatch.setattr(
        cli,
        "_run_solve",
        fake_run_solve,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rent-envy",
            "solve",
            "property.json",
            "--rent",
            "2700",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    captured = capsys.readouterr()

    assert exc_info.value.code == 2
    assert "Error: Example validation failure." in captured.err


def test_cli_end_to_end_with_real_solver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs_directory = tmp_path / "inputs"
    inputs_directory.mkdir()
    input_file = inputs_directory / "property.json"

    _write_json(
        input_file,
        {
            "friend_1": {
                "room_1": 13,
                "room_2": 10,
                "room_3": 7,
            },
            "friend_2": {
                "room_1": 7,
                "room_2": 13,
                "room_3": 10,
            },
            "friend_3": {
                "room_1": 10,
                "room_2": 7,
                "room_3": 13,
            },
        },
    )

    monkeypatch.setattr(
        cli,
        "INPUTS_DIRECTORY",
        inputs_directory,
    )

    cli._run_solve(
        input_file="property.json",
        raw_rent="30",
    )

    output = capsys.readouterr().out

    assert "Input:" in output
    assert "Final negotiated rent: £30.00" in output
    assert "RECOMMENDED ALLOCATION" in output
    assert "friend_1 -> room_1" in output
    assert "friend_2 -> room_2" in output
    assert "friend_3 -> room_3" in output
    assert "ALL ALLOCATIONS" in output
