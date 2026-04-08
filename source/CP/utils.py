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
    team1: List[List[int]],
    team2: List[List[int]],
    is_optimization: bool = False
) -> Optional[List[List[List[int]]]]:
    """
    Returns:
        Matrix (n/2) x (n-1)
        sol[period][week] = [home_team, away_team]
    """
    if result.solution is None:
        return []

    try:
        match_period = result.solution.matchPeriod
        
        # Only read swap variable in optimization version
        swap = result.solution.swap if is_optimization else None

        n_weeks = len(match_period)
        n_periods = len(match_period[0])

        # Initialize matrix: periods x weeks
        schedule = [
            [None for _ in range(n_weeks)]
            for _ in range(n_periods)
        ]

        for w in range(n_weeks):
            for k in range(n_periods):
                period = match_period[w][k] - 1  # convert to 0-index
                t1 = int(team1[w][k]) + 1   # convert to 1-index
                t2 = int(team2[w][k]) + 1

                if is_optimization and swap is not None:
                    # swap[w][k] = True means team2 is home
                    if not swap[w][k]:
                        schedule[period][w] = [t1, t2]
                    else:
                        schedule[period][w] = [t2, t1]
                else:
                    # Decision version: team_a is always home by convention
                    schedule[period][w] = [t1, t2]

        return schedule

    except Exception as e:
        print(f"Warning: Could not parse solution: {e}")
        return None
    

def format_sol(sol):  
    if sol == []:
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


def load_results(input_path: Path) -> Dict[str, Any]:
    """
    Load results from JSON file
    """
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    return data.get("results", data)