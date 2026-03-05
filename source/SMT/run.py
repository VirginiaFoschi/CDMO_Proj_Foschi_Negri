import argparse

from solve_smt import solve_smt

def main():

    parser = argparse.ArgumentParser(
        description="Tournament scheduling via Z3 SMT solver. "
                    "Only nTeams is required — everything else is derived.",
    )
    parser.add_argument(
        "--nTeams", type=int, nargs="+", default=16,
        help="Number of teams (even, >= 4). Can specify multiple.",
    )
    parser.add_argument(
        "--timeout", type=int, default=300000,
        help="Timeout in milliseconds (default: 300)",
    )
    args = parser.parse_args()

    
    result = solve_smt(
        n_teams=args.nTeams,
        timeout_ms=args.timeout,
    )


if __name__ == "__main__":
    main()