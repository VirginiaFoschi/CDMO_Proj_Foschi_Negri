import math
import time
import datetime
import minizinc
from minizinc import Instance, Model, Solver
import os
from circle_method import circle_method
from utils import parse_solution

def find_solution(n_teams, model, solver, time_limit_ms = 300000):

    instance = Instance(solver, model)

    base_a, base_b, _ = circle_method(n_teams)

    instance["nTeams"] = n_teams
    instance["baseA"] = base_a
    instance["baseB"] = base_b

    print(f"Solving for n = {n_teams}...")

    result = instance.solve(
        timeout=datetime.timedelta(milliseconds=time_limit_ms)
    )

    return parse_solution(result, base_a, base_b)

def solve_sts(nTeams, model_path, solver_name, opt=False, time_limit_ms=300000):
    """
    Solve STS problem with precomputed home/away assignments.
    """
    
    if nTeams % 2 != 0:
        raise ValueError("Number of teams must be even!")
    
    model = minizinc.Model(model_path)
    solver = minizinc.Solver.lookup(solver_name)

    result_dict = {
        "time": None,
        "optimal": False,
        "obj": None,
        "sol": None
    }
    
    # Solve
    start_time = time.time()
    result = find_solution(nTeams, model, solver, time_limit_ms)
    end_time = time.time()
    total_time = end_time - start_time
    
    result_dict["time"] = math.floor(total_time)
    result_dict["sol"] = result
    result_dict["optimal"] = opt
        
    return result_dict