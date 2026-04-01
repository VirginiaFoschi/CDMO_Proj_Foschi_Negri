import math
import time
import argparse
from pathlib import Path
from typing import List

from circle_method import circle_method
from model.model import solve_sat
from model.optimized_model import solve_sat_optimize
from model.z3_model import solve_sat_z3
from model.z3_optimized_model import solve_sat_z3_optimize
from utils import parse_solution, save_results
from config import DEFAULT_CONFIG, ModelConfig, AVAILABLE_SOLVERS


# ---------------------------------------------------------------------------
# Internal runners
# ---------------------------------------------------------------------------

def _run_pysat_decision(nTeams, symmetry_breaking, time_limit_s, solver_name):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, obj = solve_sat(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        solver_name=solver_name,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
    )
    return solved, period_sol, obj, base_a, base_b, None


def _run_pysat_optimized(nTeams, symmetry_breaking, time_limit_s, solver_name):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, obj = solve_sat_optimize(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        solver_name=solver_name,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
    )
    return solved, period_sol, obj, base_a, base_b, None


def _run_z3_decision(nTeams, symmetry_breaking, time_limit_s, solver_name=None):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, obj = solve_sat_z3(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
    )
    return solved, period_sol, obj, base_a, base_b, None


def _run_z3_optimized(nTeams, symmetry_breaking, time_limit_s, solver_name=None):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, obj = solve_sat_z3_optimize(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
    )
    return solved, period_sol, obj, base_a, base_b, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve_sts(
    nTeams: int,
    model: ModelConfig,
    symmetry_breaking: bool = True,
    time_limit_s: int = 300,
    solver_name: str = "glucose4",
) -> dict:
    if nTeams % 2 != 0:
        raise ValueError("Number of teams must be even!")

    start_time = time.time()

    if model.z3 and model.opt:
        runner = _run_z3_optimized
    elif model.z3 and not model.opt:
        runner = _run_z3_decision
    elif not model.z3 and model.opt:
        runner = _run_pysat_optimized
    else:
        runner = _run_pysat_decision

    # Z3 models ignore solver_name (Z3 has its own internal SAT engine)
    kwargs = {} if model.z3 else {"solver_name": solver_name}
    solved, period_sol, obj_value, base_a, base_b, home_sol = runner(
        nTeams, symmetry_breaking, time_limit_s, **kwargs
    )

    elapsed = time.time() - start_time

    return {
        "time":    min(math.floor(elapsed), time_limit_s),
        "optimal": solved,
        "obj":     obj_value,
        "sol":     parse_solution(period_sol, base_a, base_b, home_sol) if solved else [],
    }


def run_experiments(
    nteams_values: List[int],
    models: List[ModelConfig],
    timeout_s: int,
    sym_break: List[bool],
    solvers: List[str],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for n_teams in nteams_values:
        current_results = {}

        for model in models:
            opt_tag = "optimized" if model.opt else "decision"

            if model.z3:
                # Z3 has a single internal engine — no solver loop
                for sym in sym_break:
                    key = f"z3_{opt_tag}" + ("_symbreak" if sym else "")
                    print(f"\nRunning {key} on n={n_teams}...")
                    result = solve_sts(
                        nTeams=n_teams, model=model,
                        symmetry_breaking=sym, time_limit_s=timeout_s,
                    )
                    current_results[key] = result
                    print(f"  Backend    : Z3")
                    print(f"  Total time : {result['time']}s")
                    print(f"  Optimal    : {result['optimal']}")
                    print(f"  Obj        : {result['obj']}")
                    print(f"  Sol found  : {bool(result['sol'])}")
            else:
                # PySAT — iterate over all requested solvers
                for solver_name in solvers:
                    for sym in sym_break:
                        key = f"{solver_name}_{opt_tag}" + ("_symbreak" if sym else "")
                        print(f"\nRunning {key} on n={n_teams}...")
                        result = solve_sts(
                            nTeams=n_teams, model=model,
                            symmetry_breaking=sym, time_limit_s=timeout_s,
                            solver_name=solver_name,
                        )
                        current_results[key] = result
                        print(f"  Solver     : {solver_name}")
                        print(f"  Total time : {result['time']}s")
                        print(f"  Optimal    : {result['optimal']}")
                        print(f"  Obj        : {result['obj']}")
                        print(f"  Sol found  : {bool(result['sol'])}")

        save_results(current_results, output_dir / f"{n_teams}.json")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SAT tournament scheduling experiments"
    )
    parser.add_argument("--nteams",     type=int,  nargs="+", default=DEFAULT_CONFIG.nteams_values)
    parser.add_argument("--timeout",    type=int,             default=DEFAULT_CONFIG.timeout_s)
    parser.add_argument("--sym_break",  type=lambda x: x.lower() == "true", nargs="+",
                        default=DEFAULT_CONFIG.sym_break)
    parser.add_argument("--solvers",    type=str,  nargs="+", default=DEFAULT_CONFIG.solvers,
                        choices=AVAILABLE_SOLVERS)
    parser.add_argument("--output-dir", type=str,             default="res/SAT")
    parser.add_argument("--z3-only",    action="store_true",
                        help="Run only Z3 models (skip PySAT)")
    parser.add_argument("--pysat-only", action="store_true",
                        help="Run only PySAT models (skip Z3)")

    args = parser.parse_args()

    models = DEFAULT_CONFIG.models
    if args.z3_only:
        models = [m for m in models if m.z3]
    elif args.pysat_only:
        models = [m for m in models if not m.z3]

    run_experiments(
        nteams_values=args.nteams,
        models=models,
        timeout_s=args.timeout,
        sym_break=args.sym_break,
        solvers=args.solvers,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()


#####Sistema questione timeout#####