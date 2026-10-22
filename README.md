# Rent Envy Minimizer

A small Python CLI for allocating three bedrooms and splitting rent between three housemates in a way that minimises **maximum envy**.

Each housemate independently values the three rooms. The program converts those valuations into relative room premiums, evaluates all six possible room allocations, searches for the fairest premium/discount split for each allocation, and recommends the allocation with the lowest achievable maximum envy.

## Core idea

Suppose the final negotiated rent for a property is `R`.

Each room ultimately costs:

```text
R / 3 + p_i
```

where `p_i` is the premium or discount attached to room `i`.

The room premiums always satisfy:

```text
p_1 + p_2 + p_3 = 0
```

so any saving or increase in the negotiated total rent is shared equally through the `R / 3` component.

## Valuations

Each friend independently submits a valuation for `room_1`, `room_2`, and `room_3`.

The submitted values do **not** need to sum to the advertised rent, or even to the same total as another friend's valuations. Only the relative differences matter.

For a friend's valuations:

```text
v_1, v_2, v_3
```

their mean valuation is:

```text
mean = (v_1 + v_2 + v_3) / 3
```

and their subjective premium for room `i` is:

```text
x_i = v_i - mean
```

For example:

```text
1200, 1000, 800
```

becomes:

```text
+200, 0, -200
```

while:

```text
1700, 1500, 1300
```

produces exactly the same subjective premiums.

## Envy

For a friend, the perceived deal value of room `i` is:

```text
subjective premium - actual premium
```

If that friend is allocated room `a`, their envy of another room `i` is:

```text
deal_value(i) - deal_value(a)
```

Their personal maximum envy is the larger envy value across the two alternative rooms.

The program then defines:

```text
maximum envy = max(friend_1 envy, friend_2 envy, friend_3 envy)
```

and minimises that value.

Importantly, envy is **not** clamped to zero.

Therefore:

- positive maximum envy means at least one friend prefers another room/deal;
- zero means the allocation is envy-free, but someone is indifferent between their own room and another;
- negative means every friend strictly prefers their own allocated room;
- more negative is better.

## Premium bounds

A room cannot have negative rent.

Because:

```text
room rent = R / 3 + p_i
```

each room premium is constrained to:

```text
-R / 3 <= p_i <= 2R / 3
```

The lower bound corresponds to a room costing £0.

The upper bound corresponds to one room carrying the entire property rent while the other two rooms cost £0.

## Search strategy

There are only six possible assignments of three rooms to three friends.

For each allocation, the program performs a coarse-to-fine exhaustive search over room premiums.

### Coarse search

The full valid premium space is searched in £10 increments.

Because:

```text
p_3 = -(p_1 + p_2)
```

only `p_1` and `p_2` need to be searched independently.

Candidates are rejected if the derived premium for any room falls outside the valid rent bounds.

### Fine search

Every tied coarse optimum is retained.

The program then searches the union of the surrounding regions using £1 increments.

This avoids arbitrarily refining around only one coarse optimum.

### Multiple optimal premium splits

If several fine-grid premium combinations have the same minimum maximum-envy score, the program finds the two tied optimum points furthest apart and selects their midpoint as the representative premium split.

This allows outputs ending in 50p where appropriate.

The maximum envy is then recalculated using the representative midpoint actually returned.

## Allocation ties

More than one room allocation can occasionally achieve the same best maximum-envy score.

When this happens:

1. all tied best allocations are retained;
2. the CLI prints a warning;
3. the program selects a deterministic recommendation using lexicographic order.

This effectively favours lower-indexed friends in lower-indexed rooms where equivalent solutions exist.

## Repository structure

```text
rent-envy-minimizer/
├── .gitignore
├── README.md
├── pyproject.toml
├── inputs/
│   └── example.json
├── src/
│   └── rent_envy_minimizer/
│       ├── __init__.py
│       ├── models.py
│       ├── valuations.py
│       ├── envy.py
│       ├── search.py
│       ├── solver.py
│       └── cli.py
└── tests/
    ├── test_models.py
    ├── test_valuations.py
    ├── test_envy.py
    ├── test_search.py
    ├── test_solver.py
    └── test_cli.py
```

## Installation

The project currently requires Python 3.13 or later.

Create and activate a virtual environment, then install the package in editable mode with its development dependencies:

```bash
python -m pip install -e ".[dev]"
```

This installs the `rent-envy` command defined in `pyproject.toml`.

## Input files

Place property valuation files in:

```text
inputs/
```

Only `inputs/example.json` should be committed to the repository.

Actual valuation files should remain local and are ignored by Git.

The expected JSON structure is:

```json
{
  "friend_1": {
    "room_1": 1200,
    "room_2": 1000,
    "room_3": 800
  },
  "friend_2": {
    "room_1": 900,
    "room_2": 1250,
    "room_3": 850
  },
  "friend_3": {
    "room_1": 800,
    "room_2": 900,
    "room_3": 1300
  }
}
```

Before collecting valuations, the three friends should agree which physical bedroom is `room_1`, `room_2`, and `room_3`.

The valuations can use round numbers and do not need to total the advertised rent.

## Usage

If the valuation file is:

```text
inputs/property.json
```

run:

```bash
rent-envy solve property.json --rent 2700
```

The filename is resolved implicitly inside the `inputs/` directory.

Do **not** pass the directory itself:

```text
rent-envy solve inputs/property.json --rent 2700
```

is intentionally rejected.

The CLI expects only the filename:

```text
rent-envy solve property.json --rent 2700
```

If the file cannot be found, the CLI asks the user to place it in the `inputs/` folder and refers them to `inputs/example.json`.

## Output

The CLI displays:

- the recommended friend-to-room allocation;
- the final rent payable for each room;
- the premium or discount for each room;
- the recommended allocation's maximum-envy score;
- whether the result is strictly envy-free, envy-free, or still contains envy;
- a warning if multiple allocations tie for the best result; and
- the optimal premiums and maximum-envy score for all six room allocations.

A representative result may look like:

```text
RECOMMENDED ALLOCATION
----------------------
friend_1 -> room_2
friend_2 -> room_1
friend_3 -> room_3

ROOM RENTS
----------
room_1: £1,050.00
room_2: £850.00
room_3: £800.00

PREMIUMS / DISCOUNTS
--------------------
room_1: +£150.00
room_2: -£50.00
room_3: -£100.00

MAXIMUM ENVY
------------
-£18.00
Result: STRICTLY ENVY FREE
```

## Negotiated rent

The friends' subjective room premiums are independent of the final negotiated property rent.

For example, suppose the advertised rent is £3,000 and the agreed relative room premiums are:

```text
room_1: +£150
room_2: -£50
room_3: -£100
```

If the final negotiated rent is £2,700, the base share becomes:

```text
£2,700 / 3 = £900
```

so the final room rents are:

```text
room_1: £1,050
room_2: £850
room_3: £800
```

The £300 saving from negotiation is therefore shared equally as a £100 reduction in each friend's base share.

## Validation

The CLI validates:

- that the requested input file exists in `inputs/`;
- that the filename has a `.json` extension;
- that the JSON is syntactically valid;
- that all three required friends are present;
- that all three rooms are present for each friend;
- that valuation values are valid finite numbers;
- that there are no unexpected top-level friend fields; and
- that the final negotiated rent is a positive finite number.

Invalid input exits cleanly with a user-facing error message.

## Tests

Run the full test suite with:

```bash
pytest
```

The suite covers:

- domain models and invariants;
- valuation normalisation;
- deal values and envy calculations;
- premium bounds and grid generation;
- coarse and fine search behaviour;
- midpoint handling;
- all six room allocations;
- solver tie-breaking;
- CLI parsing, validation and output; and
- an end-to-end CLI path using the real solver.

## Linting

Run Ruff with:

```bash
ruff check .
```

## Design principles

The first version intentionally favours:

- transparent mathematics;
- deterministic results;
- exhaustive search over opaque optimisation;
- exact decimal arithmetic for money;
- clear separation between models, calculations, search, orchestration and CLI;
- minimal runtime dependencies; and
- comprehensive tests around the fairness logic.

The problem is small enough that clarity and auditability are more important than micro-optimising compute performance.
