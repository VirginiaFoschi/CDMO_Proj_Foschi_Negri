from typing import List, Tuple, Optional
from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.card import CardEnc, EncType
import math
import time as _time
import json
import os


def solve_sat_optimize(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True,
    solver_name: str = "glucose4",
    base_a: List[List[int]] = None,
    base_b: List[List[int]] = None,
    team_match_idx: List[List[int]] = None,
    checkpoint_file: str = None,
) -> Tuple[bool, List[List[int]], Optional[int]]:
    """
    Solve tournament scheduling (optimization version) with PySAT.
    Binary search on max_diff. Best solution found is written to
    checkpoint_file so the parent process can read it after a timeout.
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    def var_x(w, k, p):
        return w * n_periods * n_periods + k * n_periods + p + 1

    x_top = n_weeks * n_periods * n_periods

    def var_h(w, k):
        return x_top + w * n_periods + k + 1

    h_top = x_top + n_weeks * n_periods

    def var_hi(t, w):
        return h_top + t * n_weeks + w + 1

    hi_top = h_top + n_teams * n_weeks
    vpool_offset = hi_top + 1

    base_cnf = CNF()

    for w in range(n_weeks):
        for k in range(n_periods):
            base_cnf.append([var_x(w, k, p) for p in range(n_periods)])
    for w in range(n_weeks):
        for k in range(n_periods):
            lits = [var_x(w, k, p) for p in range(n_periods)]
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    base_cnf.append([-lits[i], -lits[j]])
    for w in range(n_weeks):
        for p in range(n_periods):
            base_cnf.append([var_x(w, k, p) for k in range(n_periods)])
            lits = [var_x(w, k, p) for k in range(n_periods)]
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    base_cnf.append([-lits[i], -lits[j]])
    for t in range(n_teams):
        for p in range(n_periods):
            lits = [var_x(w, team_match_idx[t][w], p) for w in range(n_weeks)]
            atmost2 = CardEnc.atmost(lits=lits, bound=2, top_id=vpool_offset,
                                     encoding=EncType.totalizer)
            for clause in atmost2.clauses:
                base_cnf.append(clause)
            if atmost2.clauses:
                vpool_offset = max(abs(l) for cl in atmost2.clauses for l in cl) + 1
            base_cnf.append(lits)

    for t in range(n_teams):
        for w in range(n_weeks):
            k  = team_match_idx[t][w]
            hi = var_hi(t, w)
            h  = var_h(w, k)
            if base_a[w][k] == t:
                base_cnf.append([-hi,  h])
                base_cnf.append([ hi, -h])
            else:
                base_cnf.append([-hi, -h])
                base_cnf.append([ hi,  h])

    if symm_break:
        for k in range(n_periods):
            base_cnf.append([var_x(0, k, k)])
        base_cnf.append([var_h(0, 0)])

    def save_checkpoint(period_sol, obj, h_vals):
        if checkpoint_file:
            with open(checkpoint_file, 'w') as f:
                json.dump({"period_sol": period_sol, "obj": obj, "h_vals": h_vals}, f)

    deadline = _time.time() + timeout_s
    low  = 1
    high = n_weeks
    best_period_sol = None
    best_h_vals     = None
    best_obj        = None
    found_any       = False

    while low <= high:
        if _time.time() >= deadline:
            break

        k = (low + high) // 2
        lb = math.ceil((n_weeks - k) / 2)
        ub = math.floor((n_weeks + k) / 2)

        extra_clauses = []
        vpool_k = vpool_offset

        for t in range(n_teams):
            lits = [var_hi(t, w) for w in range(n_weeks)]
            atl = CardEnc.atleast(lits=lits, bound=lb, top_id=vpool_k,
                                  encoding=EncType.totalizer)
            extra_clauses.extend(atl.clauses)
            if atl.clauses:
                vpool_k = max(abs(l) for cl in atl.clauses for l in cl) + 1
            atm = CardEnc.atmost(lits=lits, bound=ub, top_id=vpool_k,
                                 encoding=EncType.totalizer)
            extra_clauses.extend(atm.clauses)
            if atm.clauses:
                vpool_k = max(abs(l) for cl in atm.clauses for l in cl) + 1

        tmp_cnf = CNF(from_clauses=base_cnf.clauses + extra_clauses)

        if _time.time() >= deadline:
            break

        with Solver(name=solver_name, bootstrap_with=tmp_cnf) as solver:
            satisfiable = solver.solve()

            if satisfiable:
                model_vals = set(solver.get_model())
                period_sol = [
                    [next(p for p in range(n_periods)
                          if var_x(w, kk, p) in model_vals) + 1
                     for kk in range(n_periods)]
                    for w in range(n_weeks)
                ]
                # h[w][k] = True iff base_a[w][k] is home
                h_vals = [
                    [var_h(w, kk) in model_vals for kk in range(n_periods)]
                    for w in range(n_weeks)
                ]
                home_counts = [
                    sum(1 for w in range(n_weeks) if var_hi(t, w) in model_vals)
                    for t in range(n_teams)
                ]
                actual_obj = max(abs(2 * hc - n_weeks) for hc in home_counts)

                best_period_sol = period_sol
                best_h_vals     = h_vals
                best_obj        = actual_obj
                found_any       = True
                save_checkpoint(period_sol, actual_obj, h_vals)
                high = k - 1
            else:
                low = k + 1

    if found_any:
        optimal = (low > high)
        return optimal, best_period_sol, best_h_vals, best_obj
    else:
        return False, [], None, None
