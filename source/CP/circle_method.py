"""
Circle method for round-robin tournament scheduling (presolving).
"""
import time
from typing import List, Tuple
import numpy as np

def wrap_1_to_m(z: int, m: int) -> int:
        """
        Wrap value z to range 1..m
        """
        return ((((z - 1) % m) + m) % m) + 1

def circle_method(n_teams: int) -> Tuple[List[List[int]], List[List[int]], float]:
        """
        Generate round-robin pairings using circle method
        """
        start_time = time.time()

        n_weeks = n_teams - 1
        n_periods = n_teams // 2
        
        base_a = []
        base_b = []
        
        for w in range(1, n_weeks + 1):  
            week_a = []
            week_b = []
            
            for k in range(1, n_periods + 1):  
                if k == 1:
                    # First match: team 0 vs week number
                    team_a = 0
                    team_b = w
                else:
                    # Other matches: symmetric rotation
                    team_a = wrap_1_to_m(w - (k - 1), n_weeks)
                    team_b = wrap_1_to_m(w + (k - 1), n_weeks)
                
                week_a.append(team_a)
                week_b.append(team_b)
            
            base_a.append(week_a)
            base_b.append(week_b)
        
        computation_time = time.time() - start_time
        
        return base_a, base_b, computation_time