from typing import List, Tuple, Optional
from z3 import Bool, Or, Not, AtMost, AtLeast, Solver, sat, is_true
import math
import time as _time
import json


def solve_sat_z3_optimize(
    n_teams: int = None,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: List[List[int]] = None,
    base_b: List[List[int]] = None,
    team_match_idx: List[List[int]] = None,
    checkpoint_file: str = None,
) -> Tuple[bool, List[List[int]], Optional[int]]:
    """
    Solve tournament scheduling (optimization version) with Z3 SAT.
    Binary search on max_diff. Best solution found is written to
    checkpoint_file so the parent process can read it after a timeout.
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    x = [
        [[Bool(f"x_w{w}_k{k}_p{p}") for p in range(n_periods)]
         for k in range(n_periods)]
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

    base_clauses = []

    for w in range(n_weeks):
        for k in range(n_periods):
            lits = x[w][k]
            base_clauses.append(Or(lits))
            base_clauses.append(AtMost(*lits, 1))
    for w in range(n_weeks):
        for p in range(n_periods):
            lits = [x[w][k][p] for k in range(n_periods)]
            base_clauses.append(Or(lits))
            base_clauses.append(AtMost(*lits, 1))
    for t in range(n_teams):
        for p in range(n_periods):
            lits = [x[w][team_match_idx[t][w]][p] for w in range(n_weeks)]
            base_clauses.append(AtMost(*lits, 2))
            base_clauses.append(Or(lits))
    for t in range(n_teams):
        for w in range(n_weeks):
            k = team_match_idx[t][w]
            if base_a[w][k] == t:
                base_clauses.append(Or(Not(hi[t][w]),  h[w][k]))
                base_clauses.append(Or(    hi[t][w],  Not(h[w][k])))
            else:
                base_clauses.append(Or(Not(hi[t][w]), Not(h[w][k])))
                base_clauses.append(Or(    hi[t][w],      h[w][k]))

    if symm_break:
        for k in range(n_periods):
            base_clauses.append(x[0][k][k])
        base_clauses.append(h[0][0])

    def save_checkpoint(period_sol, obj):
        if checkpoint_file:
            with open(checkpoint_file, 'w') as f:
                json.dump({"period_sol": period_sol, "obj": obj}, f)

    deadline = _time.time() + timeout_s
    low  = 1
    high = n_weeks
    best_period_sol = None
    best_obj        = None
    found_any       = False

    while low <= high:
        if _time.time() >= deadline:
            break

        k = (low + high) // 2
        lb = math.ceil((n_weeks - k) / 2)
        ub = math.floor((n_weeks + k) / 2)

        s = Solver()
        remaining_ms = int((deadline - _time.time()) * 1000)
        s.set("timeout", max(remaining_ms, 1))

        for clause in base_clauses:
            s.add(clause)
        for t in range(n_teams):
            lits = [hi[t][w] for w in range(n_weeks)]
            s.add(AtLeast(*lits, lb))
            s.add(AtMost(*lits,  ub))

        result = s.check()

        if result == sat:
            m = s.model()
            period_sol = [
                [next(p for p in range(n_periods) if is_true(m.evaluate(x[w][kk][p]))) + 1
                 for kk in range(n_periods)]
                for w in range(n_weeks)
            ]
            home_counts = [
                sum(1 for w in range(n_weeks) if is_true(m.evaluate(hi[t][w])))
                for t in range(n_teams)
            ]
            actual_obj = max(abs(2 * hc - n_weeks) for hc in home_counts)

            best_period_sol = period_sol
            best_obj        = actual_obj
            found_any       = True
            save_checkpoint(period_sol, actual_obj)
            high = k - 1
        else:
            low = k + 1

    if found_any:
        optimal = (low > high)
        return optimal, best_period_sol, best_obj
    else:
        return False, [], None
