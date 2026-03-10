import math

import minizinc
import sys
import time
import datetime
import argparse
from pathlib import Path
from typing import List
from circle_method import circle_method
from model.model import solve_smt
from utils import parse_solution
from config import DEFAULT_CONFIG, ExperimentConfig, ModelConfig
from utils import save_results
import z3
from z3 import *

def solve_sts(nTeams, model, symmetry_breaking=True, time_limit_ms=300000):
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
    
    # Solve
    start_time = time.time()
    base_a, base_b, team_match_idx = circle_method(nTeams)
    opt, solution = solve_smt(nTeams, time_limit_ms, symmetry_breaking, base_a=base_a, base_b=base_b, team_match_idx=team_match_idx)
    end_time = time.time()
    total_time = end_time - start_time
    time_limit_s = time_limit_ms // 1000
    
    result_dict["time"] = min(math.floor(total_time), time_limit_s)
    result_dict["optimal"] = opt
    result_dict["sol"] = parse_solution(solution, base_a, base_b)
        
    return result_dict

def run_experiments(
    nteams_values: List[int],
    models: List[ModelConfig],
    timeout: int,
    sym_break: List[bool],
    output_dir: Path
):
    """
    Run experiments for all combinations of models, teams, and solvers
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for n_teams in nteams_values:
        current_results = {}
        for model in models:
            if model.opt:
                key = f"z3_optimized"
            else:
                key = f"z3"
            print(f"\nRunning {key}...")
            
            for sym in sym_break:

                if sym:
                    key += "_symbreak"

                result = solve_sts(
                    nTeams=n_teams,
                    model=model,
                    symmetry_breaking=sym,
                    time_limit_ms=timeout
                )

                current_results[key] = result
                
                print(f"  Total time: {result['time']}s")
                print(f"  Optimal: {result['optimal']}")
                print(f"  Solution found: {bool(result['sol'])}")
            
        output_file = output_dir / f"{n_teams}.json"
        save_results(current_results, output_file)

def main():

    parser = argparse.ArgumentParser(
        description='Run tournament scheduling experiments with multiple configurations'
    )
    parser.add_argument(
        '--nteams',
        type=int,
        nargs='+',
        default=DEFAULT_CONFIG.nteams_values,
        help='List of nTeams values to test'
    )
    parser.add_argument(
        '--models',
        type=str,
        nargs='+',
        default=DEFAULT_CONFIG.models,
        help='List of models to use'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CONFIG.timeout_s,
        help='Timeout in seconds (default: 300)'
    )
    parser.add_argument(
        '--sym_break',
        type=bool,
        nargs='+',
        default=DEFAULT_CONFIG.sym_break,
        help='Whether to use symmetry breaking'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='res/SMT',
        help='Output directory for results (default: res/SMT)'
    )
    
    args = parser.parse_args()
    
    run_experiments(
        nteams_values=args.nteams,
        models=args.models,
        timeout=args.timeout,
        sym_break=args.sym_break,
        output_dir=Path(args.output_dir)
    )


if __name__ == "__main__":
    main()