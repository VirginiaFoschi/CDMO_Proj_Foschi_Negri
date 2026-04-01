from typing import List, Tuple, Optional
from z3 import Bool, Or, Not, AtMost, AtLeast, Solver, sat, is_true
import time as _time


def solve_sat_z3_optimize(
    n_teams: int = None,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: List[List[int]] = None,
    base_b: List[List[int]] = None,
    team_match_idx: List[List[int]] = None,
) -> Tuple[bool, List[List[int]], Optional[int]]:
    """
    Solve tournament scheduling (optimization version) with Z3 SAT.

    Objective: minimise maximum home/away imbalance across all teams.
    Strategy: iterative tightening over target_imbalance in {0, 1}.
    The actual objective value is always computed from the solution.
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    # ------------------------------------------------------------------ #
    #  Decision variables                                                  #
    # ------------------------------------------------------------------ #
    x = [
        [
            [Bool(f"x_w{w}_k{k}_p{p}") for p in range(n_periods)]
            for k in range(n_periods)
        ]
        for w in range(n_weeks)
    ]
    h = [
        [Bool(f"h_w{w}_k{k}") for k in range(n_periods)]
        for w in range(n_weeks)
    ]
    hi = [
        [Bool(f"hi_t{t}_w{w}") for w in range(n_weeks)]
        for t in range(n_teams)
    ]

    # ------------------------------------------------------------------ #
    #  Base constraints                                                    #
    # ------------------------------------------------------------------ #
    base_clauses = []

    # C1/C2 – ALO + AMO per match (row)
    for w in range(n_weeks):
        for k in range(n_periods):
            lits = x[w][k]
            base_clauses.append(Or(lits))
            base_clauses.append(AtMost(*lits, 1))

    # C3 – ALO + AMO per period per week (column)
    for w in range(n_weeks):
        for p in range(n_periods):
            lits = [x[w][k][p] for k in range(n_periods)]
            base_clauses.append(Or(lits))
            base_clauses.append(AtMost(*lits, 1))

    # C4 – at-most-twice + at-least-once per team per period
    for t in range(n_teams):
        for p in range(n_periods):
            lits = [x[w][team_match_idx[t][w]][p] for w in range(n_weeks)]
            base_clauses.append(AtMost(*lits, 2))
            base_clauses.append(Or(lits))

    # C5 – link hi[t][w] <-> h[w][k] or ¬h[w][k]
    for t in range(n_teams):
        for w in range(n_weeks):
            k = team_match_idx[t][w]
            if base_a[w][k] == t:
                base_clauses.append(Or(Not(hi[t][w]),  h[w][k]))
                base_clauses.append(Or(    hi[t][w],  Not(h[w][k])))
            else:
                base_clauses.append(Or(Not(hi[t][w]), Not(h[w][k])))
                base_clauses.append(Or(    hi[t][w],      h[w][k]))

    # C6 – home count per team in [L, U]
    L = n_weeks // 2
    U = L + 1
    for t in range(n_teams):
        lits = [hi[t][w] for w in range(n_weeks)]
        base_clauses.append(AtLeast(*lits, L))
        base_clauses.append(AtMost(*lits,  U))

    # Symmetry breaking
    if symm_break:
        for k in range(n_periods):
            base_clauses.append(x[0][k][k])
        base_clauses.append(h[0][0])

    # ------------------------------------------------------------------ #
    #  Iterative tightening on max imbalance in {0, 1}                   #
    # ------------------------------------------------------------------ #
    deadline = _time.time() + timeout_s

    for target_imbalance in range(0, 2):
        if _time.time() > deadline:
            break

        # target=0 only feasible when n_weeks is even — skip otherwise
        if target_imbalance == 0 and n_weeks % 2 != 0:
            continue

        s = Solver()
        remaining_ms = int((deadline - _time.time()) * 1000)
        s.set("timeout", max(remaining_ms, 1))

        for clause in base_clauses:
            s.add(clause)

        if target_imbalance == 0 and n_weeks % 2 == 0:
            for t in range(n_teams):
                lits = [hi[t][w] for w in range(n_weeks)]
                s.add(AtLeast(*lits, L))
                s.add(AtMost(*lits,  L))  # exactly L

        result = s.check()

        if result == sat:
            m = s.model()
            period_sol = [
                [
                    next(p for p in range(n_periods) if is_true(m.evaluate(x[w][k][p])))
                    + 1
                    for k in range(n_periods)
                ]
                for w in range(n_weeks)
            ]

            # Compute actual objective from solution
            home_counts = []
            for t in range(n_teams):
                home = sum(
                    1 for w in range(n_weeks)
                    if is_true(m.evaluate(hi[t][w]))
                )
                home_counts.append(home)
            actual_obj = max(
                abs(2 * hc - n_weeks) for hc in home_counts
            )

            return True, period_sol, actual_obj

    return False, [], None
