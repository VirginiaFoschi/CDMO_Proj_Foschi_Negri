from pathlib import Path
from typing import Any, List, Dict, Optional
import json


def parse_solution(
    result,
    base_a: List[List[int]],
    base_b: List[List[int]],
    home_sol: Optional[List[List[bool]]] = None,
) -> Optional[List[List[List[int]]]]:
    """
    Parse SAT solution into the period x week matrix format required by the checker.

    Parameters
    ----------
    result    : match_period_solution[w][k] -> period (1-indexed)
    base_a    : base_a[w][k] -> team index (0-indexed) that is the 'a' side of match k in week w
    base_b    : base_b[w][k] -> team index (0-indexed) that is the 'b' side
    home_sol  : home_sol[w][k] -> True iff base_a[w][k] is the HOME team
                If None (decision version), base_a is always treated as home.
    """
    if result == []:
        return None

    try:
        match_period = result
        n_weeks   = len(match_period)
        n_periods = len(match_period[0])

        schedule = [[None for _ in range(n_weeks)] for _ in range(n_periods)]

        for w in range(n_weeks):
            for k in range(n_periods):
                period   = match_period[w][k] - 1          # 0-indexed
                team_a   = base_a[w][k] + 1                # 1-indexed for output
                team_b   = base_b[w][k] + 1

                if home_sol is not None:
                    # home_sol[w][k] = True  => base_a is home => [team_a, team_b]
                    # home_sol[w][k] = False => base_b is home => [team_b, team_a]
                    if home_sol[w][k]:
                        schedule[period][w] = [team_a, team_b]
                    else:
                        schedule[period][w] = [team_b, team_a]
                else:
                    # Decision version: base_a is always listed first (home)
                    schedule[period][w] = [team_a, team_b]

        return schedule

    except Exception as e:
        print(f"Warning: Could not parse solution: {e}")
        return None


def format_sol(sol):
    if sol is None or sol == []:
        return "[]"

    rows = []
    for row in sol:
        matches = ",".join(f"[{a},{b}]" for a, b in row)
        rows.append(f"      [{matches}]")
    return "[\n" + ",\n".join(rows) + "\n    ]"


def save_results(results: Dict[str, Any], output_path: Path):
    output = "{\n"
    solver_blocks = []

    for solver_name, solver_data in results.items():
        block  = f'  "{solver_name}": {{\n'
        block += f'    "time": {solver_data["time"]},\n'
        block += f'    "optimal": {str(solver_data["optimal"]).lower()},\n'
        block += f'    "obj": {json.dumps(solver_data["obj"])},\n'
        block += f'    "sol": {format_sol(solver_data["sol"])}\n'
        block += "  }"
        solver_blocks.append(block)

    output += ",\n".join(solver_blocks)
    output += "\n}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(output)

    print(f"Results saved to {output_path}")
