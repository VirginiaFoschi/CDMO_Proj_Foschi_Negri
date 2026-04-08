import time
from typing import Dict, List, Tuple


def wrap_1_to_m(z: int, m: int) -> int:
    """Wrap value z to range 1..m."""
    return ((((z - 1) % m) + m) % m) + 1


def circle_method(n_teams: int) -> Dict:
    """
    Generate round-robin pairings using the circle method.
    """

    n_weeks = n_teams - 1
    n_periods = n_teams // 2

    team1 = []
    team2 = []
    # team_match_idx[t][w] stores which match index 'k' team 't' plays in week 'w'
    team_match_idx = [[-1 for _ in range(n_weeks)] for _ in range(n_teams)]

    for w in range(1, n_weeks + 1):
        week_team1 = []
        week_team2 = []
        w_idx = n_weeks - w
        for k in range(1, n_periods + 1):
            if k == 1:
                t1 = 0
                t2 = w
            else:
                t1 = wrap_1_to_m(w - (k - 1), n_weeks)
                t2 = wrap_1_to_m(w + (k - 1), n_weeks)

            team_match_idx[t1][w_idx] = k-1
            team_match_idx[t2][w_idx] = k-1

            week_team1.append(t1)
            week_team2.append(t2)

        team1.append(week_team1)
        team2.append(week_team2)

    return team1, team2, team_match_idx