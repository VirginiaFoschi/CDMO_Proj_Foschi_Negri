import math
import time
import argparse
from pathlib import Path
from typing import List

from circle_method import circle_method
from model.model import solve_mip
from model.optimized_model import solve_mip_optimize
from utils import parse_solution, save_results
from config import DEFAULT_CONFIG, ModelConfig


def solve_sts(
    nTeams: int,
    model: ModelConfig,
    symmetry_breaking: bool = True,
    time_limit_s: int = 300,
    solver_type: str = "cbc",
    solver_verbose: bool = False,
):
    """
    Solve one STS instance with the MIP model.
    """

    if nTeams % 2 != 0:
        raise ValueError("Number of teams must be even!")

    result_dict = {
        "time": None,
        "optimal": False,
        "obj": None,
        "sol": None,
    }

    start_time = time.time()

    # Same preprocessing used in SMT
    base_a, base_b, team_match_idx = circle_method(nTeams)

    if model.opt:
        solved, solution, obj_value = solve_mip_optimize(
            n_teams=nTeams,
            timeout_s=time_limit_s,
            symm_break=symmetry_breaking,
            base_a=base_a,
            base_b=base_b,
            team_match_idx=team_match_idx,
            solver_type=solver_type,
            solver_verbose=solver_verbose,
        )
    else:
        solved, solution, obj_value = solve_mip(
            n_teams=nTeams,
            timeout_s=time_limit_s,
            symm_break=symmetry_breaking,
            base_a=base_a,
            base_b=base_b,
            team_match_idx=team_match_idx,
            solver_type=solver_type,
            solver_verbose=solver_verbose,
        )

    end_time = time.time()
    total_time = end_time - start_time

    result_dict["time"] = min(math.floor(total_time), time_limit_s)
    result_dict["obj"] = obj_value
    result_dict["optimal"] = solved
    result_dict["sol"] = parse_solution(solution, base_a, base_b) if solved else []

    return result_dict


def run_experiments(
    nteams_values: List[int],
    models: List[ModelConfig],
    timeout_s: int,
    sym_break: List[bool],
    solver_types: List[str],
    output_dir: Path,
    solver_verbose: bool = False,
):
    """
    Run all combinations of models, solvers and symmetry settings.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for n_teams in nteams_values:
        current_results = {}

        for model in models:
            for solver_type in solver_types:

                base_key = f"mip_{solver_type}"
                if model.opt:
                    base_key += "_optimized"

                print(f"\nRunning {base_key} for n={n_teams}...")

                for sym in sym_break:
                    key = base_key
                    if sym:
                        key += "_symbreak"

                    result = solve_sts(
                        nTeams=n_teams,
                        model=model,
                        symmetry_breaking=sym,
                        time_limit_s=timeout_s,
                        solver_type=solver_type,
                        solver_verbose=solver_verbose,
                    )

                    current_results[key] = result

                    print(f"  Total time: {result['time']}s")
                    print(f"  Optimal: {result['optimal']}")
                    print(f"  Objective: {result['obj']}")
                    print(f"  Solution found: {bool(result['sol'])}")

        output_file = output_dir / f"{n_teams}.json"
        save_results(current_results, output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Run tournament scheduling experiments with MIP models"
    )
    parser.add_argument(
        "--nteams",
        type=int,
        nargs="+",
        default=DEFAULT_CONFIG.nteams_values,
        help="List of nTeams values to test",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_CONFIG.timeout_s,
        help="Timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--sym_break",
        type=lambda x: x.lower() in ("true", "1", "yes", "t"),
        nargs="+",
        default=DEFAULT_CONFIG.sym_break,
        help="Whether to use symmetry breaking",
    )
    parser.add_argument(
        "--solvers",
        type=str,
        nargs="+",
        default=["cbc"],
        help="List of MIP solvers to use: cbc, highs, scip",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="res/MIP",
        help="Output directory for results (default: res/MIP)",
    )
    parser.add_argument(
        "--solver-verbose",
        action="store_true",
        help="Enable solver logs",
    )

    args = parser.parse_args()

    run_experiments(
        nteams_values=args.nteams,
        models=DEFAULT_CONFIG.models,
        timeout_s=args.timeout,
        sym_break=args.sym_break,
        solver_types=args.solvers,
        output_dir=Path(args.output_dir),
        solver_verbose=args.solver_verbose,
    )


if __name__ == "__main__":
    main()