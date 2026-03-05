import math
import time
from typing import Dict
from circle_method import circle_method
from model.model import build_model
from utils import extract_schedule
import z3

def solve_smt(
    n_teams: int = None,
    timeout_ms: int = 300000,
) -> Dict:
    """
    Solve tournament scheduling with Z3.
    """

    # ── Build model ─────────────────────────────────────────
    start_time = time.perf_counter()
    A, B = circle_method(n_teams)
    solver, mp = build_model(n_teams, A, B)

    build_t = time.perf_counter() - start_time

    # ── Set timeout ─────────────────────────────────────────
    solver.set("timeout", timeout_ms)

    t_solve = time.perf_counter()
    result = solver.check()
    print("Result:", result)
    solve_t = time.perf_counter() - t_solve

    total_t = build_t + solve_t
   
    z3_model = solver.model()
    schedule = extract_schedule(z3_model, mp, n_teams,A, B)
    for w, week in enumerate(schedule, 1):
        matches = [f"({m[0]:2d} vs {m[1]:2d})" if m else "(--)" for m in week]
        print(f"Week {w:2d}: {' '.join(matches)}")
    return {
        "time":          math.floor(total_t),
        "optimal":       False,
        "obj":           None,
        "sol":           schedule,
        "n_teams":       n_teams
    }


