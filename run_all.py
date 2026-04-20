import argparse
import subprocess
import sys
from pathlib import Path

MODEL_FILES = {
    "CP":  Path("source/CP/run.py"),
    "SAT": Path("source/SAT/run.py"),
    "SMT": Path("source/SMT/run.py"),
    "MIP": Path("source/MIP/run.py"),
}

SOLVERS = {
    "CP":  ["gecode",  "chuffed"],
    "SAT": ["glucose4", "cadical195", "minisat22"],
    "SMT": ["z3"], 
    "MIP": ["highs", "cbc"],
}

MODEL_TYPES = {
    "CP":  ["decision", "optimized", "optimized_dwd_luby"],
    "SAT": ["decision", "optimized"], 
    "SMT": ["decision", "optimized"], 
    "MIP": ["decision", "optimized"], 
}

ALL_PARADIGMS  = list(MODEL_FILES.keys())
ALL_NTEAMS     = [6, 8, 10, 12, 14, 16, 18, 20, 22]
DEFAULT_OUTDIR = "res"

# Sentinel: distinguishes "user passed nothing" from any real default value.
_NOT_SET = object()

def filter_solvers(requested: list[str], paradigm: str) -> list[str]:
    valid = SOLVERS[paradigm]
    if len(requested) == 1 and requested[0].lower() == "all":
        return valid  # return all valid solvers for this paradigm
    kept    = [s for s in requested if s in valid]
    dropped = [s for s in requested if s not in valid]
    if dropped:
        print(f"  [WARN] {paradigm}: ignoring invalid solver(s) {dropped} ")
    return kept


def filter_models(requested: list[str], paradigm: str) -> list[str]:
    valid = MODEL_TYPES[paradigm]
    if len(requested) == 1 and requested[0].lower() == "all":
        return valid  # return all valid models for this paradigm
    kept    = [m for m in requested if m in valid]
    dropped = [m for m in requested if m not in valid]
    if dropped:
        print(f"  [WARN] {paradigm}: ignoring invalid model(s) {dropped}")
    return kept


def build_argv(args, paradigm: str) -> list[str]:
    """
    Build the subprocess argv for one paradigm.
    Only arguments the user explicitly provided are forwarded;
    everything else is left to each run.py's own DEFAULT_CONFIG.
    """
    out_dir = Path(args.output_dir) / paradigm
    argv = [sys.executable, str(MODEL_FILES[paradigm]),
            "--output-dir", str(out_dir)]

    if args.nteams is not _NOT_SET:
        argv += ["--nteams", *[str(n) for n in args.nteams]]

    if args.timeout is not _NOT_SET:
        argv += ["--timeout", str(args.timeout)]

    if args.models is not _NOT_SET:
        kept = filter_models(args.models, paradigm)
        if kept:
            argv += ["--models", *kept]

    if args.sym_break is not _NOT_SET:
        argv += ["--sym_break", *[str(s) for s in args.sym_break]]

    if args.solvers is not _NOT_SET:
        kept = filter_solvers(args.solvers, paradigm)
        if kept:
            argv += ["--solvers", *kept]

    return argv

def run_paradigm(paradigm: str, argv: list[str], dry_run: bool) -> int:
    script = MODEL_FILES[paradigm]
    if not script.exists():
        print(f"[WARN]  {paradigm}: script not found at '{script}' — skipping.")
        return -1

    return subprocess.run(argv).returncode

class _SetSentinel(argparse.Action):
    """Store the value and mark it as explicitly set (overrides _NOT_SET default)."""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Unified runner — CP / SAT / SMT / MIP experiments"
    )

    parser.add_argument(
        "-p","--paradigms", nargs="+", default=["all"], metavar="PARADIGM",
        help=f"Paradigms to run: any of {ALL_PARADIGMS} or 'all'. (default: all)",
    )

    parser.add_argument(
        "-n", "--nteams", nargs="+", default=_NOT_SET, action=_SetSentinel, metavar="N",
        help="Team sizes e.g. 6 8 10, or 'all' for the full default list. "
             "(default: each paradigm's own default)",
    )
    parser.add_argument(
        "-s", "--solvers", nargs="+", default=_NOT_SET, action=_SetSentinel, metavar="SOLVER",
        help="Solvers to request. Invalid ones per paradigm are skipped with a warning. "
             "(default: each paradigm's own default)",
    )
    parser.add_argument(
        "-m", "--models", nargs="+", default=_NOT_SET, action=_SetSentinel, metavar="MODEL",
        help="Models to use, forwarded uniformly. "
             "(default: each paradigm's own default)",
    )
    parser.add_argument(
        "-t", "--timeout", type=int, default=_NOT_SET, action=_SetSentinel, metavar="S",
        help="Timeout per run in seconds, forwarded uniformly. "
             "(default: each paradigm's own default)",
    )
    parser.add_argument(
        "-sym", "--sym_break", nargs="+", default=_NOT_SET, action=_SetSentinel,
        type=str,
        metavar="BOOL",
        help="Symmetry breaking: True/False (or T/F), forwarded uniformly. "
             "(default: each paradigm's own default)",
    )
    parser.add_argument(
        "-o", "--output-dir", default=DEFAULT_OUTDIR,
        help=f"Base output dir. Each paradigm writes to <dir>/<PARADIGM>/. "
             f"(default: {DEFAULT_OUTDIR})",
    )

    return parser.parse_args()


def resolve_paradigms(raw: list[str]) -> list[str]:
    if len(raw) == 1 and raw[0].lower() == "all":
        return ALL_PARADIGMS
    unknown = [p for p in raw if p not in MODEL_FILES]
    if unknown:
        print(f"[ERROR] Unknown paradigm(s): {unknown}. Valid: {ALL_PARADIGMS}")
        sys.exit(1)
    return raw


def resolve_nteams(raw) -> list[int]:
    if raw is _NOT_SET:
        return _NOT_SET
    try:
        return [int(x) for x in raw]
    except ValueError as e:
        print(f"[ERROR] --nteams must be integers: {e}")
        sys.exit(1)

def resolve_sym_break(raw) -> list[bool]:
    if raw is _NOT_SET:
        return _NOT_SET
    if len(raw) == 1 and raw[0] == "both":
        return [True, False]
    return [x.lower() in ("true", "1", "yes", "t") for x in raw]

def main():
    args = parse_args()

    args.paradigms = resolve_paradigms(args.paradigms)
    args.nteams    = resolve_nteams(args.nteams)
    args.sym_break = resolve_sym_break(args.sym_break)

    def fmt(val):
        return "default" if val is _NOT_SET else val

    print(f"\nUnified Experiment Runner")
    print(f"  Paradigms  : {args.paradigms}")
    print(f"  nTeams     : {fmt(args.nteams)}")
    print(f"  Solvers    : {fmt(args.solvers)}")
    print(f"  Models     : {fmt(args.models)}")
    print(f"  Timeout    : {fmt(args.timeout)}")
    print(f"  Sym break  : {fmt(args.sym_break)}")
    print(f"  Output     : {args.output_dir}/<PARADIGM>/")

    failed = []

    for paradigm in args.paradigms:
        argv = build_argv(args, paradigm)
        rc   = run_paradigm(paradigm, argv, dry_run=False)

        if rc not in (0, -1):
            print(f"\n[ERROR] {paradigm} exited with code {rc}, continuing...")
            failed.append((paradigm, rc))

    for paradigm in args.paradigms:
        status = "FAILED" if any(p == paradigm for p, _ in failed) else "OK"
        print(f"  {paradigm:<6}  {status}")

    if failed:
        print(f"\n{len(failed)} paradigm(s) finished with errors.")
        sys.exit(1)
    else:
        print("\nAll paradigms completed successfully.")


if __name__ == "__main__":
    main()


# Examples: (uses the default values in paradigm's run.py for everything not explicitly set here)
# python run_all.py --p CP MIP --s gecode highs --n 6 8 --sym True
# python run_all.py --p all --s all --n 6 8 --sym both
# python run_all.py --p all
# python run_all.py --p CP