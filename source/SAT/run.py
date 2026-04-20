import math
import time
import argparse
import signal
import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional

from circle_method import circle_method
from model.model import solve_sat
from model.optimized_model import solve_sat_optimize
from model.z3_model import solve_sat_z3
from model.z3_optimized_model import solve_sat_z3_optimize
from utils import parse_solution, save_results
from config import DEFAULT_CONFIG, ModelConfig, AVAILABLE_SOLVERS


# ---------------------------------------------------------------------------
# Fork-based hard timeout with checkpoint support
# ---------------------------------------------------------------------------

def _run_with_timeout(fn, args, timeout_s):
    r_fd, w_fd = os.pipe()
    pid = os.fork()

    if pid == 0:
        # Child
        os.close(r_fd)
        import pickle
        try:
            result = fn(*args)
            data = pickle.dumps(("ok", result))
        except Exception as e:
            data = pickle.dumps(("err", str(e)))
        with os.fdopen(w_fd, "wb") as f:
            f.write(data)
        os._exit(0)
    else:
        # Parent
        os.close(w_fd)
        deadline = time.time() + timeout_s
        child_done = False

        while time.time() < deadline:
            result_pid, _ = os.waitpid(pid, os.WNOHANG)
            if result_pid != 0:
                child_done = True
                break
            time.sleep(0.1)

        if not child_done:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
            os.close(r_fd)
            return None  # timeout

        import pickle
        with os.fdopen(r_fd, "rb") as f:
            data = f.read()

        if not data:
            return None

        status, payload = pickle.loads(data)
        if status == "ok":
            return payload
        else:
            raise RuntimeError(f"Worker error: {payload}")


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


def _run_pysat_optimized(nTeams, symmetry_breaking, time_limit_s, solver_name, checkpoint_file):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, home_sol, obj = solve_sat_optimize(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        solver_name=solver_name,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
        checkpoint_file=checkpoint_file,
    )
    return solved, period_sol, obj, base_a, base_b, home_sol


def _run_z3_decision(nTeams, symmetry_breaking, time_limit_s):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, obj = solve_sat_z3(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
    )
    return solved, period_sol, obj, base_a, base_b, None


def _run_z3_optimized(nTeams, symmetry_breaking, time_limit_s, checkpoint_file):
    base_a, base_b, team_match_idx = circle_method(nTeams)
    solved, period_sol, home_sol, obj = solve_sat_z3_optimize(
        n_teams=nTeams, timeout_s=time_limit_s, symm_break=symmetry_breaking,
        base_a=base_a, base_b=base_b, team_match_idx=team_match_idx,
        checkpoint_file=checkpoint_file,
    )
    return solved, period_sol, obj, base_a, base_b, home_sol


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

    # For optimized models use a checkpoint file to recover best solution on timeout
    checkpoint_file = None
    if model.opt:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        checkpoint_file = tmp.name
        tmp.close()

    if model.z3 and model.opt:
        fn, args = _run_z3_optimized, (nTeams, symmetry_breaking, time_limit_s, checkpoint_file)
    elif model.z3 and not model.opt:
        fn, args = _run_z3_decision, (nTeams, symmetry_breaking, time_limit_s)
    elif not model.z3 and model.opt:
        fn, args = _run_pysat_optimized, (nTeams, symmetry_breaking, time_limit_s, solver_name, checkpoint_file)
    else:
        fn, args = _run_pysat_decision, (nTeams, symmetry_breaking, time_limit_s, solver_name)

    # Precompute base_a/base_b in parent for parse_solution after timeout
    base_a, base_b, _ = circle_method(nTeams)

    start_time = time.time()
    raw = _run_with_timeout(fn, args, timeout_s=time_limit_s)
    elapsed = time.time() - start_time

    if raw is None:
        print(f"  [TIMEOUT] Hard limit of {time_limit_s}s exceeded.")

        # Try to recover best solution from checkpoint
        best_period_sol = None
        best_home_sol   = None
        best_obj        = None
        if checkpoint_file and os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file) as f:
                    ckpt = json.load(f)
                best_period_sol = ckpt.get("period_sol")
                best_obj        = ckpt.get("obj")
                best_home_sol   = ckpt.get("h_vals")
            except Exception:
                pass
            os.unlink(checkpoint_file)

        if best_period_sol:
            return {
                "time":    time_limit_s,
                "optimal": False,
                "obj":     best_obj,
                "sol":     parse_solution(best_period_sol, base_a, base_b, best_home_sol),
            }
        else:
            return {
                "time":    time_limit_s,
                "optimal": False,
                "obj":     None,
                "sol":     [],
            }

    # Clean up checkpoint file if child completed normally
    if checkpoint_file and os.path.exists(checkpoint_file):
        os.unlink(checkpoint_file)

    solved, period_sol, obj_value, base_a, base_b, home_sol = raw
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
    parser.add_argument('-n', '--nteams',     type=int,  nargs="+", default=DEFAULT_CONFIG.nteams_values)
    parser.add_argument('-t', '--timeout',    type=int,             default=DEFAULT_CONFIG.timeout_s)
    parser.add_argument('-sym', '--sym_break',  type=lambda x: x.lower() == "true", nargs="+",
                        default=DEFAULT_CONFIG.sym_break)
    parser.add_argument('-s', '--solvers',    type=str,  nargs="+", default=DEFAULT_CONFIG.solvers,
                        choices=AVAILABLE_SOLVERS)
    parser.add_argument('-o', '--output-dir', type=str,             default="res/SAT")
    parser.add_argument("--z3-only",    action="store_true")
    parser.add_argument("--pysat-only", action="store_true")

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
