import math
import time
import datetime
import minizinc
from minizinc import Instance, Model, Solver
import os
from circle_method import circle_method
from utils import parse_solution

def find_solution(n_teams, model, solver, symmetry_breaking, time_limit_ms = 300000):

    instance = Instance(solver, model)

    base_a, base_b, precomputation_time = circle_method(n_teams)

    instance["nTeams"] = n_teams
    instance["baseA"] = base_a
    instance["baseB"] = base_b
    instance["sym_break"] = symmetry_breaking

    print(f"Solving for n = {n_teams}...")
    print(f"  Symmetry breaking: {symmetry_breaking}")

    remaining_time_ms = time_limit_ms - precomputation_time
    result = instance.solve(
        timeout=datetime.timedelta(milliseconds=remaining_time_ms)
    )

    obj = result.objective
    optimal = result.status.has_solution()
    solution = parse_solution(result, base_a, base_b) if optimal else None

    return obj, optimal, solution

def solve_sts(nTeams, model, solver_name, symmetry_breaking=True, time_limit_ms=300000):
    """
    Solve STS problem with precomputed home/away assignments.
    """
    
    if nTeams % 2 != 0:
        raise ValueError("Number of teams must be even!")
    
    result_dict = {
        "time": None,
        "optimal": False,
        "obj": None,
        "sol": None
    }

    model = minizinc.Model(model.path)
    solver = minizinc.Solver.lookup(solver_name)
    
    # Solve
    start_time = time.time()
    obj, optimal, solution = find_solution(nTeams, model, solver, symmetry_breaking, time_limit_ms)
    end_time = time.time()
    total_time = end_time - start_time
    
    result_dict["time"] = math.floor(total_time)
    result_dict["optimal"] = optimal
    result_dict["obj"] = obj
    result_dict["sol"] = solution
        
    return result_dict