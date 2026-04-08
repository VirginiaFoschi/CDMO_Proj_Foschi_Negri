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
        
        team1 = []
        team2 = []
        
        for w in range(1, n_weeks + 1):  
            week_team1 = []
            week_team2 = []
            
            for k in range(1, n_periods + 1):  
                if k == 1:
                    # First match: team 0 vs week number
                    t1 = 0
                    t2 = w
                else:
                    # Other matches: symmetric rotation
                    t1 = wrap_1_to_m(w - (k - 1), n_weeks)
                    t2 = wrap_1_to_m(w + (k - 1), n_weeks)
                
                week_team1.append(t1)
                week_team2.append(t2)
            
            team1.append(week_team1)
            team2.append(week_team2)
        
        computation_time_ms = (time.time() - start_time) * 1000
        
        return team1, team2, computation_time_ms