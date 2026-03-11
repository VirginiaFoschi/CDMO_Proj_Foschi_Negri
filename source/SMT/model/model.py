from typing import Dict
import z3
from z3 import *

def solve_smt(
    n_teams: int = None,
    timeout_s: int = 300,
    symm_break: bool = True, 
    base_a: list = None,
    base_b: list = None,    
    team_match_idx: list = None
) -> Dict:
    """
    Solve tournament scheduling with Z3.
    """
    n_weeks = n_teams - 1
    n_periods = n_teams // 2
    
    s = Then('card2bv','smt').solver()
    s.set(timeout=timeout_s*1000)

    # ---- Decision Variables ----
    # match_period[w][k] is the period assigned to match k in week w
    match_period = [
        [Int(f"p_w{w}_k{k}") for k in range(n_periods)] 
        for w in range(n_weeks)
    ]

    # match_period[w][k] is an integer between 1 and n_periods
    for w in range(n_weeks):
        for k in range(n_periods):
            s.add(match_period[w][k] >= 1)
            s.add(match_period[w][k] <= n_periods)

    # ----- Constraints ------

    # 1) AllDifferent per Week: In any given week, you cannot have two matches happening in the exact same period
    # For every period 'p', exactly one match 'k' in this week uses it.
    for w in range(n_weeks):
        for p in range(1, n_periods + 1):
            # The expression (match_period[w][k] == p) becomes a Boolean for the solver. 
            # For week w and period p, look at all matches k. How many of them are assigned to period p? The constraint requires the sum to be exactly 1
            s.add(PbEq([(match_period[w][k] == p, 1) for k in range(n_periods)], 1))

    # 2) Every team plays at most twice in the same period
    for t in range(n_teams):
        for p in range(1, n_periods + 1):
            # How many weeks does team t play in period p?
            occurrences = [(match_period[w][team_match_idx[t][w]] == p, 1)
                        for w in range(n_weeks)]
            s.add(PbGe(occurrences, 1))  # at least once
            s.add(PbLe(occurrences, 2))  # at most twice


    # ---- Symmetry Breaking ----
    if symm_break:
        # Break Period Symmetry: first week periods are 1, 2, 3...
        for k in range(n_periods):
            s.add(match_period[0][k] == k + 1)

    # --- Solve -----
    result = s.check()
    if result == sat:
        m = s.model()

        # matrix of size N_WEEKS X N_PERIODS, where each entry is the period assigned to that match in that week. For example: match_period_solution[0] = [1, 2, 3, 4] means that for week 0: match 0->period 1, match 1->period 2,
        match_period_solution = [
            [m.evaluate(match_period[w][k]).as_long() for k in range(n_periods)]
            for w in range(n_weeks)
        ]

        #return optimal, solution, objective value (in this case None since we are not optimizing anything)
        return True, match_period_solution, None
    else:
        return False, [], None