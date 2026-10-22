# Rent Envy Minimizer

A Python tool for fairly allocating three bedrooms and splitting rent between three housemates.

Each housemate independently submits their own valuation of the three rooms. The algorithm considers every possible allocation of rooms and searches for a rent split that minimises the maximum envy experienced by any housemate.

The final result recommends:

- who should receive each room;
- the premium or discount associated with each room;
- the resulting rent payable by each housemate; and
- the level of envy associated with the optimal solution.

## Motivation

Bedrooms in a shared property are rarely identical.

One room might be larger, another might have an en-suite, and another might have worse storage or natural light. Splitting the total rent equally therefore does not necessarily produce a fair outcome.

Rather than negotiating room values after deciding who gets each room, each housemate privately evaluates all three rooms.

The algorithm then attempts to find the room allocation and rent split that makes everyone as satisfied as possible with their own deal relative to the alternatives.

## Room Naming

Rooms are identified generically as:

- `room_1`
- `room_2`
- `room_3`

The three housemates should agree which physical bedroom corresponds to each identifier before submitting their valuations.

Housemates are similarly identified as:

- `friend_1`
- `friend_2`
- `friend_3`

## Valuations

Each friend independently submits a monetary valuation for each room.

For example:

```text
friend_1:
    room_1: 1200
    room_2: 1000
    room_3: 800
```

The valuations do **not** need to sum to the property's advertised rent.

A friend should simply provide values that represent the relative amounts they believe the rooms are worth.

For friend `j`, let their submitted valuations be:

```text
v_j1, v_j2, v_j3
```

Their mean room valuation is:

```text
mean_j = (v_j1 + v_j2 + v_j3) / 3
```

Each valuation is converted into a subjective room premium:

```text
x_ji = v_ji - mean_j
```

Therefore:

```text
x_j1 + x_j2 + x_j3 = 0
```

Only the relative valuations of the rooms matter.

For example, the submission:

```text
1200, 1000, 800
```

becomes:

```text
+200, 0, -200
```

## Actual Room Premiums

The algorithm searches for actual premiums or discounts:

```text
p_1, p_2, p_3
```

subject to:

```text
p_1 + p_2 + p_3 = 0
```

Only two dimensions therefore need to be searched explicitly:

```text
p_3 = -p_1 - p_2
```

If the final negotiated rent for the property is `R`, the actual rent for room `i` is:

```text
rent_i = R / 3 + p_i
```

Negotiating the total rent does not change the premiums and discounts implied by the friends' valuations.

For example, if the advertised rent is £3,000 but the final negotiated rent is £2,700, the £300 saving reduces the base share of each housemate by £100.

## Premium Bounds

No room may have a negative rent.

Because:

```text
rent_i = R / 3 + p_i
```

each premium is bounded by:

```text
-R / 3 <= p_i <= 2R / 3
```

The lower bound corresponds to a room with zero rent.

The upper bound corresponds to one room carrying the entire rent while the other two rooms have zero rent.

Candidate solutions outside these bounds are invalid.

## Deal Value

For friend `j`, the perceived deal value of room `i` is:

```text
D_ji = x_ji - p_i
```

where:

- `x_ji` is that friend's subjective premium for the room; and
- `p_i` is the actual premium charged for the room.

A positive deal value means the friend believes the room is cheap relative to their valuation.

A negative deal value means they believe it is expensive relative to their valuation.

## Envy

Suppose friend `j` is allocated room `a(j)`.

Their envy of room `i` is:

```text
E_ji = D_ji - D_j,a(j)
```

The friend's maximum envy is their most attractive alternative room:

```text
E_j = max(E_ji for all i != a(j))
```

The overall maximum envy for a candidate solution is:

```text
E_max = max(E_1, E_2, E_3)
```

The objective of the algorithm is to **minimise `E_max`**.

Importantly, envy is not clamped to zero.

Therefore:

```text
E_max > 0
```

means at least one friend would prefer another room at the proposed prices.

```text
E_max = 0
```

means the allocation is envy-free, but at least one friend is indifferent between their own room and an alternative.

```text
E_max < 0
```

means every friend strictly prefers their own allocated room to either alternative.

A more negative maximum-envy score is therefore preferable.

## Room Allocations

There are three friends and three rooms, giving:

```text
3! = 6
```

possible allocations.

The algorithm evaluates all six.

For each allocation, it finds the premium/discount combination that minimises maximum envy.

The globally preferred solution is the allocation with the lowest achievable maximum envy.

## Search Strategy

The initial implementation uses an exhaustive coarse-to-fine grid search.

### Stage 1: Coarse Search

Search the valid premium space in increments of:

```text
£10
```

Because the premiums sum to zero, only two premiums need to be independently searched.

For every candidate:

```text
p_3 = -p_1 - p_2
```

The candidate is discarded if any room premium lies outside:

```text
[-R/3, 2R/3]
```

The maximum envy is calculated for every valid candidate.

### Stage 2: Fine Search

The regions surrounding the best coarse-grid solution or solutions are searched again using increments of:

```text
£1
```

This produces the final minimum maximum-envy score for that room allocation.

If multiple adjacent £10 coarse-grid points are optimal, the fine search should cover the union of the neighbourhoods surrounding all coarse optima rather than refining around an arbitrary single point.

## Multiple Optimal Premium Splits

It is possible for multiple premium combinations to produce the same minimum maximum-envy score.

The algorithm retains the optimal region rather than arbitrarily selecting the first point encountered during the search.

Where a continuum or range of equally optimal solutions exists, the algorithm selects the midpoint as the representative premium split.

A midpoint ending in 50 pence is acceptable even though the main fine search uses £1 increments.

The selected premiums must continue to satisfy:

```text
p_1 + p_2 + p_3 = 0
```

## Allocation Ties

More than one room allocation may occasionally produce an equivalent optimal result, particularly where friends have identical or equivalent room preferences.

When an allocation tie occurs, the program should:

1. report that an equivalent allocation exists;
2. apply a deterministic tie-break; and
3. prefer the lower-indexed friend in the lower-indexed room where the symmetry permits this.

This ensures repeated runs produce the same recommendation.

## Final Rent Calculation

Once the optimal allocation and room premiums have been selected, the final negotiated property rent `R` is applied.

For each room:

```text
rent_i = R / 3 + p_i
```

The final rents must sum to exactly `R`.

Example:

```text
Final negotiated rent: £2,700

Base share: £900

room_1 premium:  +£150
room_2 premium:   -£50
room_3 premium:  -£100
```

produces:

```text
room_1: £1,050
room_2:   £850
room_3:   £800
----------------
total:  £2,700
```

## CLI

The first version of the project will use a command-line interface.

The intended workflow is:

1. The three friends inspect the property.
2. They agree which bedrooms are `room_1`, `room_2`, and `room_3`.
3. Each friend privately submits their valuation of the three rooms.
4. The valuations are collected outside this program.
5. The valuations are supplied to the CLI.
6. The final negotiated rent is supplied.
7. The algorithm evaluates all six room allocations.
8. The recommended allocation and rent split are displayed.

A future CLI might resemble:

```bash
rent-envy solve valuations.json --rent 2700
```

The exact input format and CLI syntax will be finalised during implementation.

## Intended Output

The output should show the recommended allocation prominently, for example:

```text
RECOMMENDED ALLOCATION
----------------------

friend_1 -> room_2
friend_2 -> room_1
friend_3 -> room_3

ROOM RENTS
----------

room_1: £1,050
room_2:   £850
room_3:   £800

PREMIUMS / DISCOUNTS
--------------------

room_1: +£150
room_2:  -£50
room_3: -£100

MAXIMUM ENVY
------------

-£18

ENVY FREE
```

For completeness, the program should also report the optimal result for each of the six possible room allocations rather than displaying only the globally recommended allocation.

## Project Structure

The intended initial structure is:

```text
rent-envy-minimizer/
├── .gitignore
├── README.md
├── pyproject.toml
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
    ├── test_valuations.py
    ├── test_envy.py
    ├── test_search.py
    └── test_solver.py
```

The core algorithm should remain independent of the CLI so that other interfaces can be added later without changing the optimisation logic.

## Development

Install the project in editable mode with the development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the tests with:

```bash
pytest
```

Run linting with:

```bash
ruff check .
```

## Design Principles

The initial implementation should favour:

- simple and transparent mathematics;
- deterministic results;
- exhaustive evaluation over opaque optimisation;
- comprehensive unit tests;
- minimal dependencies;
- separation between the optimisation engine and user interface.

The problem is intentionally small enough that clarity and auditability are more important than optimising computational performance.
