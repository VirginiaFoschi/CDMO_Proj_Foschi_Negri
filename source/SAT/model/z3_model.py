from typing import List, Tuple, Optional
from z3 import Bool, And, Or, Not, Implies, AtMost, AtLeast, Solver, sat


def solve_sat_z3(
    n_teams: int = None,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: List[List[int]] = None,
    base_b: List[List[int]] = None,
    team_match_idx: List[List[int]] = None,
) -> Tuple[bool, List[List[int]], None]:
    """
    Solve tournament scheduling (decision version) with Z3 SAT.

    Encoding: one-hot over periods.
      x[w][k][p] = True  iff  match k in week w is assigned to period p.

    Unlike the SMT model (which uses integer variables), this model uses
    only propositional Boolean variables and encodes all constraints as
    clauses, making it a pure SAT encoding on top of Z3.
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    # ------------------------------------------------------------------ #
    #  Decision variables: x[w][k][p]                                     #
    # ------------------------------------------------------------------ #
    x = [
        [
            [Bool(f"x_w{w}_k{k}_p{p}") for p in range(n_periods)]
            for k in range(n_periods)
        ]
        for w in range(n_weeks)
    ]

    s = Solver()
    s.set("timeout", timeout_s * 1000)

    # ------------------------------------------------------------------ #
    #  C1 – At-least-one: every match gets some period                    #
    #  C2 – At-most-one:  every match gets at most one period             #
    # ------------------------------------------------------------------ #
    for w in range(n_weeks):
        for k in range(n_periods):
            lits = x[w][k]
            s.add(Or(lits))                    # ALO
            s.add(AtMost(*lits, 1))            # AMO

    # ------------------------------------------------------------------ #
    #  C3 – AllDifferent per week: each period used by exactly one match  #
    # ------------------------------------------------------------------ #
    for w in range(n_weeks):
        for p in range(n_periods):
            lits = [x[w][k][p] for k in range(n_periods)]
            s.add(Or(lits))                    # ALO (column)
            s.add(AtMost(*lits, 1))            # AMO (column)

    # ------------------------------------------------------------------ #
    #  C4 – At-most-twice + at-least-once per team per period             #
    # ------------------------------------------------------------------ #
    for t in range(n_teams):
        for p in range(n_periods):
            lits = [x[w][team_match_idx[t][w]][p] for w in range(n_weeks)]
            s.add(AtMost(*lits, 2))            # at most twice
            s.add(Or(lits))                    # at least once

    # ------------------------------------------------------------------ #
    #  Symmetry breaking: fix week 0 -> match k goes to period k         #
    # ------------------------------------------------------------------ #
    if symm_break:
        for k in range(n_periods):
            s.add(x[0][k][k])

    # ------------------------------------------------------------------ #
    #  Solve                                                               #
    # ------------------------------------------------------------------ #
    result = s.check()

    if result == sat:
        m = s.model()
        match_period_solution = [
            [
                next(p for p in range(n_periods) if m.evaluate(x[w][k][p]))
                + 1
                for k in range(n_periods)
            ]
            for w in range(n_weeks)
        ]
        return True, match_period_solution, None
    else:
        return False, [], None
