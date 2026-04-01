from typing import Dict, List, Tuple, Optional
from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.card import CardEnc, EncType


def solve_sat(
    n_teams: int = None,
    timeout_s: int = 300,
    symm_break: bool = True,
    solver_name: str = "glucose4",
    base_a: List[List[int]] = None,
    base_b: List[List[int]] = None,
    team_match_idx: List[List[int]] = None,
) -> Tuple[bool, List[List[int]], None]:
    """
    Solve tournament scheduling (decision version) with PySAT.

    Encoding: one-hot over periods.
      x[w][k][p] = True  iff  match k in week w is assigned to period (p+1).
    Variable index (1-based, DIMACS):
      var(w, k, p) = w * n_periods^2  +  k * n_periods  +  p  +  1
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    # ------------------------------------------------------------------ #
    #  Variable mapping                                                    #
    # ------------------------------------------------------------------ #
    def var(w: int, k: int, p: int) -> int:
        return w * n_periods * n_periods + k * n_periods + p + 1

    top_var = n_weeks * n_periods * n_periods

    cnf = CNF()

    # ------------------------------------------------------------------ #
    #  C1 – At-least-one: every match gets some period                    #
    # ------------------------------------------------------------------ #
    for w in range(n_weeks):
        for k in range(n_periods):
            cnf.append([var(w, k, p) for p in range(n_periods)])

    # ------------------------------------------------------------------ #
    #  C2 – At-most-one: every match gets at most one period (pairwise)   #
    # ------------------------------------------------------------------ #
    for w in range(n_weeks):
        for k in range(n_periods):
            lits = [var(w, k, p) for p in range(n_periods)]
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    cnf.append([-lits[i], -lits[j]])

    # ------------------------------------------------------------------ #
    #  C3 – AllDifferent per week: each period used by exactly one match  #
    # ------------------------------------------------------------------ #
    for w in range(n_weeks):
        for p in range(n_periods):
            cnf.append([var(w, k, p) for k in range(n_periods)])   # ALO
            lits = [var(w, k, p) for k in range(n_periods)]
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    cnf.append([-lits[i], -lits[j]])               # AMO

    # ------------------------------------------------------------------ #
    #  C4 – At-most-twice + at-least-once per team per period             #
    # ------------------------------------------------------------------ #
    vpool_offset = top_var + 1

    for t in range(n_teams):
        for p in range(n_periods):
            lits = [var(w, team_match_idx[t][w], p) for w in range(n_weeks)]

            atmost2 = CardEnc.atmost(
                lits=lits, bound=2, top_id=vpool_offset, encoding=EncType.totalizer
            )
            for clause in atmost2.clauses:
                cnf.append(clause)
            if atmost2.clauses:
                vpool_offset = max(abs(l) for cl in atmost2.clauses for l in cl) + 1

            cnf.append(lits)   # at-least-one

    # ------------------------------------------------------------------ #
    #  Symmetry breaking: fix week 0 → match k goes to period k          #
    # ------------------------------------------------------------------ #
    if symm_break:
        for k in range(n_periods):
            cnf.append([var(0, k, k)])

    # ------------------------------------------------------------------ #
    #  Solve                                                               #
    # ------------------------------------------------------------------ #
    with Solver(name=solver_name, bootstrap_with=cnf) as solver:
        satisfiable = solver.solve()

        if satisfiable:
            model_vals = set(solver.get_model())
            match_period_solution = [
                [
                    next(p for p in range(n_periods) if var(w, k, p) in model_vals) + 1
                    for k in range(n_periods)
                ]
                for w in range(n_weeks)
            ]
            return True, match_period_solution, None
        else:
            return False, [], None
