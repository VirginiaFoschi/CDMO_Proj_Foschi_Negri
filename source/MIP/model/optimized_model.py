from typing import List, Optional, Tuple
import math
from pyomo.environ import (
    ConcreteModel, RangeSet, Var, Binary, Integers,
    Constraint, ConstraintList, Objective, minimize,
    SolverFactory, value as pyomo_value
)


def _solve(model, solver_type: str, timeout_s: int, verbose: bool):
    sf_name = solver_type.lower()
    if sf_name == "highs":
        sf_name = "appsi_highs"

    sf = SolverFactory(sf_name)

    if sf_name == "cbc":
        sf.options["sec"]     = timeout_s
        sf.options["threads"] = 1
    elif sf_name == "glpk":
        sf.options["tmlim"] = timeout_s
    elif sf_name == "appsi_highs":
        sf.options["time_limit"] = timeout_s

    return sf.solve(model, tee=verbose, timelimit=timeout_s)


def _check_status(result) -> bool:
    try:
        tc = str(result.solver.termination_condition).lower()
        solved = tc in ("optimal", "feasible", "maxtimelimit", "other")
        try:
            ub = result.Problem.Upper_bound
            if ub is None or ub > 1e29:
                solved = False
        except Exception:
            pass
        return solved
    except Exception:
        return False


def _extract_periods(model, n_weeks: int, n_periods: int) -> List[List[int]]:
    match_period_solution = []
    for w in range(n_weeks):
        week_solution = []
        for k in range(n_periods):
            assigned_period = None
            for p in range(1, n_periods + 1):
                val = pyomo_value(model.x[w, k, p])
                if val is not None and val > 0.5:
                    assigned_period = p
                    break
            if assigned_period is None:
                raise RuntimeError(f"No assigned period for week {w}, match {k}")
            week_solution.append(assigned_period)
        match_period_solution.append(week_solution)
    return match_period_solution


def solve_mip_optimize(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: Optional[List[List[int]]] = None,
    base_b: Optional[List[List[int]]] = None,
    team_match_idx: Optional[List[List[int]]] = None,
    solver_type: str = "cbc",
    solver_verbose: bool = False,
) -> Tuple[bool, List[List[int]], Optional[int]]:
    """
    Optimization version of the MIP model (Pyomo).
    Uses result.Problem.Upper_bound to recover obj even on timeout.
    """
    if n_teams % 2 != 0:
        raise ValueError("Number of teams must be even.")
    if base_a is None or base_b is None or team_match_idx is None:
        raise ValueError("base_a, base_b, and team_match_idx must be provided.")

    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    model   = ConcreteModel()
    model.W = RangeSet(0, n_weeks - 1)
    model.K = RangeSet(0, n_periods - 1)
    model.P = RangeSet(1, n_periods)

    model.x = Var(model.W, model.K, model.P, domain=Binary)
    model.h = Var(model.W, model.K, domain=Binary)

    def one_period_rule(m, w, k):
        return sum(m.x[w, k, p] for p in m.P) == 1
    model.one_period = Constraint(model.W, model.K, rule=one_period_rule)

    def one_match_per_period_rule(m, w, p):
        return sum(m.x[w, k, p] for k in m.K) == 1
    model.one_match_per_period = Constraint(model.W, model.P, rule=one_match_per_period_rule)

    model.max_twice = ConstraintList()
    for t in range(n_teams):
        for p in range(1, n_periods + 1):
            model.max_twice.add(
                sum(model.x[w, team_match_idx[t][w], p] for w in range(n_weeks)) <= 2
            )

    if symm_break:
        model.sb = ConstraintList()
        for k in range(n_periods):
            model.sb.add(model.x[0, k, k + 1] == 1)
        model.sb.add(model.h[0, 0] == 1)

    # H[t] = linear expression for home games of team t
    H = {}
    for t in range(n_teams):
        home_terms = []
        for w in range(n_weeks):
            k = team_match_idx[t][w]
            if base_a[w][k] == t:
                home_terms.append(model.h[w, k])
            else:
                home_terms.append(1 - model.h[w, k])
        H[t] = sum(home_terms)

    # z = maximum imbalance
    # Lower bound = 1: n_weeks always odd (n always even)
    # Upper bound = n_weeks: worst case all home or all away
    model.z = Var(domain=Integers, bounds=(1, n_weeks))

    model.imbalance = ConstraintList()
    for t in range(n_teams):
        model.imbalance.add(model.z >= 2 * H[t] - n_weeks)
        model.imbalance.add(model.z >= n_weeks - 2 * H[t])

    model.obj = Objective(expr=model.z, sense=minimize)

    result = _solve(model, solver_type, timeout_s, solver_verbose)

    solved = _check_status(result)

    # Recover best obj from Upper_bound even on timeout
    obj_value = None
    try:
        ub = result.Problem.Upper_bound
        if ub is not None and ub < n_weeks:
            obj_value = int(math.floor(ub + 1e-6))
    except Exception:
        pass

    if not solved:
        return False, [], obj_value

    match_period_solution = _extract_periods(model, n_weeks, n_periods)
    obj_value = int(round(pyomo_value(model.z)))
    return True, match_period_solution, obj_value
