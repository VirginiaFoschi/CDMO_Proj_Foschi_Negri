from typing import Dict, List, Tuple, Any
import z3
from z3 import *

def solve_smt_optimize(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True, 
    base_a: List[List[int]] = None, 
    base_b: List[List[int]] = None,    
    team_match_idx: List[List[int]] = None
) -> Tuple[bool, int, List[List[int]], List[List[bool]]]:
    """
    Solve tournament scheduling with Z3
    """
    n_weeks = n_teams - 1
    n_periods = n_teams // 2
    
    # Optimize solver
    opt = Optimize()
    opt.set(timeout=timeout_s*1000)

    # ---- Decision Variables ----
    # match_period[w][k] is the period assigned to match k in week w
    match_period = [
        [Int(f"p_w{w}_k{k}") for k in range(n_periods)] 
        for w in range(n_weeks)
    ]
    
    # is_home_a[w][k] is BOOLEAN
    # True  => base_a[w][k] is home
    # False => base_b[w][k] is home
    is_home_a = [
        [Bool(f"ha_w{w}_k{k}") for k in range(n_periods)]
        for w in range(n_weeks)
    ]

    # match_period[w][k] is an integer between 1 and n_periods
    for w in range(n_weeks):
        for k in range(n_periods):
            opt.add(match_period[w][k] >= 1)
            opt.add(match_period[w][k] <= n_periods)

    # ----- Constraints ------

    # 1) AllDifferent per Week: In any given week, you cannot have two matches happening in the exact same period
    # For every period 'p', exactly one match 'k' in this week uses it.
    for w in range(n_weeks):
        for p in range(1, n_periods + 1):
            opt.add(PbEq([(match_period[w][k] == p, 1) for k in range(n_periods)], 1))

    # 2) Every team plays at most twice in the same period
    for t in range(n_teams):
        for p in range(1, n_periods + 1):
            # How many weeks does team t play in period p?
            occurrences = [(match_period[w][team_match_idx[t][w]] == p, 1)
                        for w in range(n_weeks)]
            opt.add(PbGe(occurrences, 1))  # at least once
            opt.add(PbLe(occurrences, 2))  # at most twice

    # ---- Symmetry Breaking ----
    if symm_break:
        # Break Period Symmetry: first week periods are 1, 2, 3...
        for k in range(n_periods):
            opt.add(match_period[0][k] == k + 1)
            # Fix the first match of first week to avoid Home/Away swap symmetry
            opt.add(is_home_a[0][0] == True)

    ## --- Optimization -----

    # A single integer variable that will track the worst-case difference between home and away games across all team
    max_imbalance = Int('max_imbalance')

    # L = 1 (lower bound), U = n - 1 (upper bound)
    opt.add(max_imbalance >= 1)
    opt.add(max_imbalance <= n_teams - 1)

    opt.add(max_imbalance % 2 == 1)
    
    for t in range(n_teams):
        # calculate number of home games for team t: this list will store 1 if the team plays at home in a week, 0 otherwise
        home_count = []
        
        for w in range(n_weeks):
            k = team_match_idx[t][w]
            
            # If team t is base_a: home if is_home_a == True
            # If team t is base_b: home if is_home_a == False
            if base_a[w][k] == t:
                home_count.append(If(is_home_a[w][k], 1, 0))
            else:
                home_count.append(If(is_home_a[w][k], 0, 1))
        
        # total number of home games for team t
        h_t = Sum(home_count)
        
        # Difference = |Home - Away|
        # Since Away = (n_weeks - Home), Diff = |2*Home - n_weeks|
        diff_val = (2 * h_t) - n_weeks
        
        # Force max_imbalance to be >= the absolute difference for this team
        opt.add(max_imbalance >= diff_val)
        opt.add(max_imbalance >= -diff_val)

    # Minimize the maximum imbalance
    opt.minimize(max_imbalance)

    # ---- Solve ----
    result = opt.check()
    if result == sat:
        m = opt.model()

        # get the Objective Value
        obj_val = m.evaluate(max_imbalance).as_long()

        # matrix of size N_WEEKS X N_PERIODS, where each entry is the period assigned to that match in that week. For example: match_period_solution[0] = [1, 2, 3, 4] means that for week 0: match 0->period 1, match 1->period 2,
        match_period_solution = [
            [m.evaluate(match_period[w][k]).as_long() for k in range(n_periods)]
            for w in range(n_weeks)
        ]

        #return optimal, solution, objective value
        return True, match_period_solution, obj_val
    else:
        return False, [], None