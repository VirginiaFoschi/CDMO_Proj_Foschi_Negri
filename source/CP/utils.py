"""
Utility functions for experiment management.
"""
import json
from pathlib import Path
import re
from typing import List, Optional, Any, Dict
from datetime import datetime
import minizinc
from minizinc import Result

def parse_solution(
    result: Result,
    base_a: List[List[int]],
    base_b: List[List[int]]
) -> Optional[List[List[List[int]]]]:
    """
    Returns:
        Matrix (n/2) x (n-1)
        sol[period][week] = [team1, team2]
    """
    if result.solution is None:
        return None

    try:
        match_period = result.solution.matchPeriod

        n_weeks = len(match_period)
        n_periods = len(match_period[0])  # should be n/2

        # Initialize matrix: periods x weeks
        schedule = [
            [None for _ in range(n_weeks)]
            for _ in range(n_periods)
        ]

        for w in range(n_weeks):
            for k in range(n_periods):
                period = match_period[w][k] - 1  # convert to 0-index
                team_a = int(base_a[w][k]) + 1
                team_b = int(base_b[w][k]) + 1 # convert to 1-index

                schedule[period][w] = [team_a, team_b]

        return schedule

    except Exception as e:
        print(f"Warning: Could not parse solution: {e}")
        return None

def format_sol(sol):
    if sol is None:
        return 'null'
    
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


def load_results(input_path: Path) -> Dict[str, Any]:
    """
    Load results from JSON file
    """
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    return data.get("results", data)