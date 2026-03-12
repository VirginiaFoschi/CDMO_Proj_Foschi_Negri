from pathlib import Path
from typing import Any, List, Dict, Optional
import json


def parse_solution(
    result,
    base_a: List[List[int]],
    base_b: List[List[int]]
) -> Optional[List[List[List[int]]]]:
    if result == []:
        return None

    try:
        match_period = result

        n_weeks = len(match_period)
        n_periods = len(match_period[0])

        # periods x weeks
        schedule = [
            [None for _ in range(n_weeks)]
            for _ in range(n_periods)
        ]

        for w in range(n_weeks):
            for k in range(n_periods):
                period = match_period[w][k] - 1
                team_a = base_a[w][k] + 1
                team_b = base_b[w][k] + 1

                schedule[period][w] = [team_a, team_b]

        return schedule

    except Exception as e:
        print(f"Warning: Could not parse solution: {e}")
        return None


def format_sol(sol):
    if sol == [] or sol is None:
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
        block = f'  "{solver_name}": {{\n'
        block += f'    "time": {solver_data["time"]},\n'
        block += f'    "optimal": {str(solver_data["optimal"]).lower()},\n'
        block += f'    "obj": {json.dumps(solver_data["obj"])},\n'
        block += f'    "sol": {format_sol(solver_data["sol"])}\n'
        block += "  }"
        solver_blocks.append(block)

    output += ",\n".join(solver_blocks)
    output += "\n}"

    with open(output_path, "w") as f:
        f.write(output)

    print(f"Results saved to {output_path}")