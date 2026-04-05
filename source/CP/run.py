import minizinc
import sys
from datetime import time
import argparse
from pathlib import Path
from typing import List
from solve_sts import solve_sts
from utils import parse_solution
from config import DEFAULT_CONFIG, MODELS, ExperimentConfig, ModelConfig
from utils import save_results

def run_experiments(
    nteams_values: List[int],
    solvers: List[str],
    models: List[ModelConfig],
    timeout_s: int,
    sym_break: List[bool],
    output_dir: Path,
    solver_verbose=False
):
    """
    Run experiments for all combinations of models, teams, and solvers
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for n_teams in nteams_values:
        current_results = {}
        for model in models:
            for solver_name in solvers:
                if model.opt:
                    key = f"{solver_name}_{model.name}"
                else:
                    key = f"{solver_name}"
                print(f"\nRunning {key}...")
                
                for sym in sym_break:

                    if sym:
                        key += "_symbreak"

                    result = solve_sts(
                        nTeams=n_teams,
                        model=model,
                        solver_name=solver_name,
                        symmetry_breaking=sym,
                        is_optimization=model.opt,
                        time_limit_s=timeout_s
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
        '--solvers',
        type=str,
        nargs='+',
        default=DEFAULT_CONFIG.solvers,
        help='List of solvers to use'
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
        type=lambda x: x.lower() in ("true", "1", "yes", "t"),
        nargs='+',
        default=DEFAULT_CONFIG.sym_break,
        help='Whether to use symmetry breaking'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='res/CP',
        help='Output directory for results (default: res/CP)'
    )

    args = parser.parse_args()

    selected_models = [MODELS[m] for m in args.models]
    
    run_experiments(
        nteams_values=args.nteams,
        solvers=args.solvers,
        models=selected_models,
        timeout_s=args.timeout,
        sym_break=args.sym_break,
        output_dir=Path(args.output_dir)
    )


if __name__ == "__main__":
    main()

# docker build -t project-solver .

# docker run -it --rm `
#    -v ${PWD}:/app `
#   -w /app `
#   --entrypoint bash `
#   project-solver

# python source/CP/run.py

