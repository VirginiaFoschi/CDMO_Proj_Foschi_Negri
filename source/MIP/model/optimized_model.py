import os
import signal
import pickle
import time as _time
from typing import List, Optional, Tuple
from pyomo.environ import (
    ConcreteModel, RangeSet, Var, Binary, NonNegativeIntegers,
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

# Seconds to wait beyond solver's own time_limit before sending SIGKILL.
_KILL_BUFFER = 30


# ---------------------------------------------------------------------------
# Solution extraction
# ---------------------------------------------------------------------------

def _extract_periods(model, n_weeks: int, n_periods: int) -> List[List[int]]:
    match_period_solution = []
    for w in range(n_weeks):
        week_solution = []
        for k in range(n_periods):
            assigned_period = None
            for p in range(1, n_periods + 1):
                try:
                    val = pyomo_value(model.x[w, k, p])
                    if val is not None and val > 0.5:
                        assigned_period = p
                        break
                except Exception:
                    pass
            if assigned_period is None:
                raise RuntimeError(
                    f"No assigned period for week {w}, match {k}")
            week_solution.append(assigned_period)
        match_period_solution.append(week_solution)
    return match_period_solution


def _extract_home(model, n_weeks: int, n_periods: int) -> dict:
    """Extract h[w,k] values: 1 means base_a is home, 0 means base_b is home."""
    h_vals = {}
    for w in range(n_weeks):
        for k in range(n_periods):
            try:
                val = pyomo_value(model.h[w, k])
                h_vals[(w, k)] = 1 if (val is not None and val > 0.5) else 0
            except Exception:
                h_vals[(w, k)] = 1  # default: base_a is home
    return h_vals


def _compute_actual_obj(h_vals: dict, base_a, base_b, team_match_idx,
                        n_teams: int, n_weeks: int) -> int:
    """Compute the actual max imbalance from extracted h values."""
    home_counts = []
    for t in range(n_teams):
        hc = 0
        for w in range(n_weeks):
            k = team_match_idx[t][w]
            if h_vals.get((w, k), 1) == 1:
                if base_a[w][k] == t:
                    hc += 1
            else:
                if base_b[w][k] == t:
                    hc += 1
        home_counts.append(hc)
    return max(abs(2 * hc - n_weeks) for hc in home_counts)


# ---------------------------------------------------------------------------
# Model builder
# ---------------------------------------------------------------------------

def _build_model(n_teams: int, symm_break: bool,
                 base_a, team_match_idx) -> ConcreteModel:
    """
    Build the optimization MIP.

    Minimizes max_imbalance = max_t |2*H[t] - (n-1)| directly,
    using the standard min-max linearization:

        max_imbalance >= 2*H[t] - (n-1)   for all t
        max_imbalance >= -(2*H[t] - (n-1)) for all t
        minimize max_imbalance

    This lets the solver find incumbents early and improve them over time,
    so a partial (non-optimal) solution is always available at timeout.
    """
    n_weeks   = n_teams - 1
    n_periods = n_teams // 2

    model   = ConcreteModel()
    model.W = RangeSet(0, n_weeks - 1)
    model.K = RangeSet(0, n_periods - 1)
    model.P = RangeSet(1, n_periods)

    # Period assignment variables
    model.x = Var(model.W, model.K, model.P, domain=Binary)
    # Home/away variables: h[w,k]=1 means base_a is home
    model.h = Var(model.W, model.K, domain=Binary)
    # Objective variable: max imbalance across all teams.
    # Lower bound = 1: since n_weeks is odd and 2*H[t] is even,
    # |2*H[t] - n_weeks| >= 1 always.
    model.max_imbalance = Var(domain=NonNegativeIntegers,
                              bounds=(1, n_weeks))

    # Implied parity: 2*H[t] - n_weeks is always odd (even - odd),
    # so max_imbalance must be odd. Encode as max_imbalance = 2*k_aux + 1.
    model.k_aux = Var(domain=NonNegativeIntegers,
                      bounds=(0, (n_weeks - 1) // 2))
    model.parity_con = Constraint(expr=model.max_imbalance == 2 * model.k_aux + 1)

    # --- Scheduling constraints ---

    # Each match assigned to exactly one period per week
    model.one_period = Constraint(
        model.W, model.K,
        rule=lambda m, w, k: sum(m.x[w, k, p] for p in m.P) == 1)

    # Each period used by exactly one match per week
    model.one_match_per_period = Constraint(
        model.W, model.P,
        rule=lambda m, w, p: sum(m.x[w, k, p] for k in m.K) == 1)

    # Each team plays at most twice in the same period over the tournament
    model.max_twice = ConstraintList()
    for t in range(n_teams):
        for p in range(1, n_periods + 1):
            model.max_twice.add(
                sum(model.x[w, team_match_idx[t][w], p]
                    for w in range(n_weeks)) <= 2)

    # --- Symmetry breaking ---
    if symm_break:
        model.sb = ConstraintList()
        for k in range(n_periods):
            model.sb.add(model.x[0, k, k + 1] == 1)
        model.sb.add(model.h[0, 0] == 1)

    # --- Min-max linearization for home/away balance ---
    # H[t] = number of home games for team t
    # max_imbalance >= |2*H[t] - n_weeks| for all t
    model.imbalance_ub = ConstraintList()
    model.imbalance_lb = ConstraintList()
    for t in range(n_teams):
        home_terms = []
        for w in range(n_weeks):
            k = team_match_idx[t][w]
            if base_a[w][k] == t:
                home_terms.append(model.h[w, k])
            else:
                home_terms.append(1 - model.h[w, k])
        H_t = sum(home_terms)
        diff = 2 * H_t - n_weeks
        model.imbalance_ub.add(model.max_imbalance >= diff)
        model.imbalance_lb.add(model.max_imbalance >= -diff)

    model.obj = Objective(expr=model.max_imbalance, sense=minimize)

    return model


# ---------------------------------------------------------------------------
# Child-process worker
# ---------------------------------------------------------------------------

def _child_work(w_fd: int, n_teams: int, symm_break: bool,
                base_a, base_b, team_match_idx,
                sf_name: str, timeout_s: int, verbose: bool) -> None:
    """
    Build model, solve, extract solution and write result to pipe.
    Called only in the forked child process; always ends with os._exit().
    """
    try:
        n_weeks   = n_teams - 1
        n_periods = n_teams // 2

        model = _build_model(n_teams, symm_break, base_a, team_match_idx)

        sf = SolverFactory(sf_name)
        sf.options[_TIMEOUT_OPT[sf_name]] = timeout_s
        sf.options["threads"] = 1
        if sf_name == "appsi_highs":
            try:
                sf.config.time_limit = float(timeout_s)
                sf.config.threads = 1
            except Exception:
                pass

        result = sf.solve(model, tee=verbose, load_solutions=True)
        tc = str(result.solver.termination_condition).lower()
        has_solution = tc in ("optimal", "feasible", "maxtimelimit", "other",
                               "aborted")
        is_optimal = (tc == "optimal")

        if not has_solution:
            payload = pickle.dumps(("no_sol",))
        else:
            period_sol = _extract_periods(model, n_weeks, n_periods)
            h_vals     = _extract_home(model, n_weeks, n_periods)
            actual_obj = _compute_actual_obj(
                h_vals, base_a, base_b, team_match_idx, n_teams, n_weeks)
            payload = pickle.dumps(("ok", is_optimal, period_sol, h_vals, actual_obj))

    except Exception as exc:
        payload = pickle.dumps(("err", str(exc)))

    with os.fdopen(w_fd, "wb") as f:
        f.write(payload)
    os._exit(0)


# ---------------------------------------------------------------------------
# Main solver function
# ---------------------------------------------------------------------------

def solve_mip_optimize(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: Optional[List[List[int]]] = None,
    base_b: Optional[List[List[int]]] = None,
    team_match_idx: Optional[List[List[int]]] = None,
    solver_type: str = "highs",
    solver_verbose: bool = False,
) -> Tuple[bool, List[List[int]], dict, Optional[int]]:
    """
    Optimization MIP model: min max_t |2*H[t] - (n-1)|

    Runs the solver in a forked child process so it can be killed with
    SIGKILL if it ignores its own time_limit (which appsi_highs sometimes
    does for hard instances).

    Returns (optimal, period_solution, h_vals, obj_value).
    """
    if n_teams % 2 != 0:
        raise ValueError("Number of teams must be even.")
    if base_a is None or base_b is None or team_match_idx is None:
        raise ValueError("base_a, base_b, and team_match_idx must be provided.")

    sf_name = _SOLVER_MAP.get(solver_type.lower())
    if sf_name is None:
        raise ValueError(
            f"solver_type must be one of {set(_SOLVER_MAP)}, got '{solver_type}'")

    r_fd, w_fd = os.pipe()
    pid = os.fork()

    if pid == 0:
        # ---- child ----
        os.close(r_fd)
        _child_work(w_fd, n_teams, symm_break, base_a, base_b, team_match_idx,
                    sf_name, timeout_s, solver_verbose)
        # _child_work always calls os._exit(); this line is never reached.

    # ---- parent ----
    os.close(w_fd)
    deadline    = _time.time() + timeout_s + _KILL_BUFFER
    child_done  = False

    while _time.time() < deadline:
        wpid, _ = os.waitpid(pid, os.WNOHANG)
        if wpid != 0:
            child_done = True
            break
        _time.sleep(0.1)

    if not child_done:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        os.close(r_fd)
        return False, [], {}, None

    with os.fdopen(r_fd, "rb") as f:
        data = f.read()

    if not data:
        return False, [], {}, None

    try:
        parts = pickle.loads(data)
    except Exception:
        return False, [], {}, None

    status = parts[0]
    if status == "ok":
        _, is_optimal, period_sol, h_vals, actual_obj = parts
        return is_optimal, period_sol, h_vals, actual_obj
    else:
        return False, [], {}, None
