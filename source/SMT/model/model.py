from typing import Dict
import z3
from z3 import *

def solve_smt(
    n_teams: int = None,
    timeout_ms: int = 300000,
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
    s.set(timeout=300*1000)

    # ---------------------------------------------------------
    # 2. Decision Variables (Integers)
    # ---------------------------------------------------------
    # match_period[w][k] is an INTEGER between 1 and n_periods
    match_period = [
        [Int(f"p_w{w}_k{k}") for k in range(n_periods)] 
        for w in range(n_weeks)
    ]

    # Domain Constraints (1..nPeriods)
    for w in range(n_weeks):
        for k in range(n_periods):
            s.add(match_period[w][k] >= 1)
            s.add(match_period[w][k] <= n_periods)

    # ---------------------------------------------------------
    # 3. Constraints (Using PB logic on Integer Expressions)
    # ---------------------------------------------------------

    # A. AllDifferent per Week
    # For every period 'p', exactly one match 'k' in this week uses it.
    for w in range(n_weeks):
        for p in range(1, n_periods + 1):
            # The expression (match_period[w][k] == p) becomes a Boolean for the solver
            s.add(PbEq([(match_period[w][k] == p, 1) for k in range(n_periods)], 1))

    # B. Team Period Balancing (Global Cardinality)
    # "Every team plays at most twice in the same period"
    for t in range(n_teams):
        for p in range(1, n_periods + 1):
            # How many weeks does team t play in period p?
            occurrences = [(match_period[w][team_match_idx[t][w]] == p, 1)
                        for w in range(n_weeks)]
            s.add(PbGe(occurrences, 1))  # at least once
            s.add(PbLe(occurrences, 2))  # at most twice

    # C. Symmetry Breaking
    if symm_break:
        # First week is 1, 2, 3...
        for k in range(n_periods):
            s.add(match_period[0][k] == k + 1)

    # ---------------------------------------------------------
    # 4. Solve
    # ---------------------------------------------------------
    result = s.check()
    print(f"Z3 result: {result}")
    if result == sat:
        m = s.model()

        match_period_solution = [
            [m.evaluate(match_period[w][k]).as_long() for k in range(n_periods)]
            for w in range(n_weeks)
        ]
        print(match_period_solution)

        return True, match_period_solution
    else:
        return False, []