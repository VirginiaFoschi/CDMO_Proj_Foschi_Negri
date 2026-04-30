import threading
from typing import List, Optional, Tuple
from pyomo.environ import (
    ConcreteModel, RangeSet, Var, Binary, Integers,
    Constraint, ConstraintList, Objective, minimize,
    SolverFactory, value as pyomo_value
)


_SOLVER_MAP = {
    "highs": "appsi_highs",
    "cbc":   "cbc",
}

_TIMEOUT_OPT = {
    "appsi_highs": "time_limit",
    "cbc":         "seconds",
}

_THREAD_TIMEOUT_BUFFER = 60


def _solve(model, solver_name: str, timeout_s: int, verbose: bool):
    """Two-layer timeout: solver-level + Python thread-level fallback."""
    sf_name = _SOLVER_MAP.get(solver_name.lower())
    if sf_name is None:
        raise ValueError(
            f"solver_type must be one of {set(_SOLVER_MAP)}, got '{solver_name}'")

    sf = SolverFactory(sf_name)
    sf.options[_TIMEOUT_OPT[sf_name]] = timeout_s
    sf.options["threads"] = 1
    if sf_name == "appsi_highs":
        try:
            sf.config.time_limit = float(timeout_s)
            sf.config.threads = 1
        except Exception:
            pass

    result_box = [None]
    error_box  = [None]

    def _target():
        try:
            result_box[0] = sf.solve(model, tee=verbose, load_solutions=True)
        except Exception as exc:
            error_box[0] = exc

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout_s + _THREAD_TIMEOUT_BUFFER)

    if t.is_alive() or error_box[0] is not None or result_box[0] is None:
        return None, False

    result = result_box[0]
    tc = str(result.solver.termination_condition).lower()
    # CBC reports status='aborted' when it hits the time limit with a
    # feasible solution; treat it the same as maxtimelimit.
    has_solution = tc in ("optimal", "feasible", "maxtimelimit", "other",
                           "aborted")
    return result, has_solution


def _extract_home(model, n_weeks: int, n_periods: int) -> dict:
    """Extract h[w,k] values: 1 means base_a is home, 0 means base_b is home.
    Uses .value directly to avoid Pyomo error messages on uninitialized vars
    (h is unconstrained in the decision model, so the solver may leave it unset)."""
    h_vals = {}
    for w in range(n_weeks):
        for k in range(n_periods):
            val = model.h[w, k].value  # None if uninitialized, no error printed
            h_vals[(w, k)] = 1 if (val is None or val > 0.5) else 0
    return h_vals


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


def solve_mip(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: Optional[List[List[int]]] = None,
    base_b: Optional[List[List[int]]] = None,
    team_match_idx: Optional[List[List[int]]] = None,
    solver_type: str = "highs",
    solver_verbose: bool = False,
) -> Tuple[bool, List[List[int]], dict, None]:
    """Decision version of the MIP model (Pyomo)."""
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

    model.obj = Objective(expr=0, sense=minimize)

    _, has_solution = _solve(model, solver_type, timeout_s, solver_verbose)

    if not has_solution:
        return False, [], {}, None

    periods = _extract_periods(model, n_weeks, n_periods)
    h_vals  = _extract_home(model, n_weeks, n_periods)
    return True, periods, h_vals, None
