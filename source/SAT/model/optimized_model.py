from typing import List, Tuple, Optional
from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.card import CardEnc, EncType
import time as _time


def solve_sat_optimize(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True,
    solver_name: str = "glucose4",
    base_a: List[List[int]] = None,
    base_b: List[List[int]] = None,
    team_match_idx: List[List[int]] = None,
) -> Tuple[bool, List[List[int]], Optional[int]]:
    """
    Solve tournament scheduling (optimization version) with PySAT.

    Objective: minimise maximum home/away imbalance across all teams.
    Strategy: iterative tightening over target_imbalance in {0, 1}.

    NOTE: target_imbalance=0 is only feasible when n_weeks is even
    (i.e. n is odd, but n must be even by problem definition, so n_weeks
    is always odd and the minimum achievable imbalance is always 1).
    We still attempt target=0 for correctness but skip the extra equality
    constraint when n_weeks is odd, letting the solver decide feasibility.
    The actual objective value is always computed from the solution.
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    # ------------------------------------------------------------------ #
    #  Variable layout (1-based DIMACS)                                   #
    # ------------------------------------------------------------------ #
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

    cnf = CNF()

    # ------------------------------------------------------------------ #
    #  Period constraints                                                  #
    # ------------------------------------------------------------------ #
    for w in range(n_weeks):
        for k in range(n_periods):
            cnf.append([var_x(w, k, p) for p in range(n_periods)])
    for w in range(n_weeks):
        for k in range(n_periods):
            lits = [var_x(w, k, p) for p in range(n_periods)]
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    cnf.append([-lits[i], -lits[j]])
    for w in range(n_weeks):
        for p in range(n_periods):
            cnf.append([var_x(w, k, p) for k in range(n_periods)])
            lits = [var_x(w, k, p) for k in range(n_periods)]
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    cnf.append([-lits[i], -lits[j]])
    for t in range(n_teams):
        for p in range(n_periods):
            lits = [var_x(w, team_match_idx[t][w], p) for w in range(n_weeks)]
            atmost2 = CardEnc.atmost(lits=lits, bound=2, top_id=vpool_offset,
                                     encoding=EncType.totalizer)
            for clause in atmost2.clauses:
                cnf.append(clause)
            if atmost2.clauses:
                vpool_offset = max(abs(l) for cl in atmost2.clauses for l in cl) + 1
            cnf.append(lits)

    # ------------------------------------------------------------------ #
    #  Home/away constraints                                              #
    # ------------------------------------------------------------------ #
    for t in range(n_teams):
        for w in range(n_weeks):
            k  = team_match_idx[t][w]
            hi = var_hi(t, w)
            h  = var_h(w, k)
            if base_a[w][k] == t:
                cnf.append([-hi,  h]);  cnf.append([ hi, -h])
            else:
                cnf.append([-hi, -h]);  cnf.append([ hi,  h])

    L = n_weeks // 2
    U = L + 1
    for t in range(n_teams):
        lits = [var_hi(t, w) for w in range(n_weeks)]
        for enc_fn, bound in [(CardEnc.atleast, L), (CardEnc.atmost, U)]:
            enc = enc_fn(lits=lits, bound=bound, top_id=vpool_offset,
                         encoding=EncType.totalizer)
            for clause in enc.clauses:
                cnf.append(clause)
            if enc.clauses:
                vpool_offset = max(abs(l) for cl in enc.clauses for l in cl) + 1

    # ------------------------------------------------------------------ #
    #  Symmetry breaking                                                  #
    # ------------------------------------------------------------------ #
    if symm_break:
        for k in range(n_periods):
            cnf.append([var_x(0, k, k)])
        cnf.append([var_h(0, 0)])

    # ------------------------------------------------------------------ #
    #  Optimise: iterative tightening on max imbalance in {0, 1}         #
    # ------------------------------------------------------------------ #
    deadline = _time.time() + timeout_s

    for target_imbalance in range(0, 2):
        if _time.time() > deadline:
            break

        # target=0 is only feasible when n_weeks is even — skip otherwise
        if target_imbalance == 0 and n_weeks % 2 != 0:
            continue

        extra_clauses = []
        if target_imbalance == 0 and n_weeks % 2 == 0:
            for t in range(n_teams):
                lits = [var_hi(t, w) for w in range(n_weeks)]
                eq = CardEnc.equals(lits=lits, bound=L, top_id=vpool_offset,
                                    encoding=EncType.totalizer)
                extra_clauses.extend(eq.clauses)
                if eq.clauses:
                    vpool_offset = max(abs(l) for cl in eq.clauses for l in cl) + 1

        tmp_cnf = CNF(from_clauses=cnf.clauses + extra_clauses)

        with Solver(name=solver_name, bootstrap_with=tmp_cnf) as solver:
            if _time.time() > deadline:
                break
            satisfiable = solver.solve()

            if satisfiable:
                model_vals = set(solver.get_model())
                period_sol = [
                    [next(p for p in range(n_periods)
                          if var_x(w, k, p) in model_vals) + 1
                     for k in range(n_periods)]
                    for w in range(n_weeks)
                ]

                # Compute actual objective from solution
                home_counts = []
                for t in range(n_teams):
                    home = sum(
                        1 for w in range(n_weeks)
                        if var_hi(t, w) in model_vals
                    )
                    home_counts.append(home)
                actual_obj = max(
                    abs(2 * hc - n_weeks) for hc in home_counts
                )

                return True, period_sol, actual_obj

    return False, [], None
