import minizinc
import sys
from datetime import time
import argparse
from pathlib import Path
from typing import List
from solve_sts import solve_sts
from utils import parse_solution
from config import DEFAULT_CONFIG, ExperimentConfig
from utils import save_results

def run_experiments(
    nteams_values: List[int],
    solvers: List[str],
    timeout: int,
    output_dir: Path,
    opt: bool = False
):
    """
    Run experiments for all combinations of models, teams, and solvers
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if opt:
        model_path = "source/CP/model/optimized_model.mzn"
    else:
        model_path = "source/CP/model/model.mzn"

    for n_teams in nteams_values:
    
        current_results = {}   
        
        for solver_name in solvers:
            print(f"\nRunning {solver_name}...")
            
            result = solve_sts(
                model_path=model_path,
                solver_name=solver_name,
                nTeams=n_teams,
                time_limit_ms=timeout
            )
            
            current_results[solver_name] = result
            
            print(f"  Total time: {result['time']}s")
            print(f"  Optimal: {result['optimal']}")
            print(f"  Solution found: {result['sol'] is not None}")
        
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
        '--solvers',
        type=str,
        nargs='+',
        default=DEFAULT_CONFIG.solvers,
        help='List of solvers to use'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CONFIG.timeout_ms,
        help='Timeout in milliseconds (default: 300000)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='res/CP',
        help='Output directory for results (default: res/CP)'
    )
    parser.add_argument(
        '--opt',
        type=int,
        default=False,
        help='use optimized model (default: False)'
    )
    
    args = parser.parse_args()
    
    run_experiments(
        nteams_values=args.nteams,
        solvers=args.solvers,
        timeout=args.timeout,
        output_dir=Path(args.output_dir),
        opt=bool(args.opt)
    )


if __name__ == "__main__":
    main()

# docker build -t project-solver .

# docker run --rm `
#    -v ${PWD}:/app `
#   -w /app `
#   project-solver

