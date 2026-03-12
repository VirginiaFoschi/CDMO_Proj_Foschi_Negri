from typing import List, Tuple


def wrap_1_to_m(z: int, m: int) -> int:
    """Wrap value z to range 1..m."""
    return ((((z - 1) % m) + m) % m) + 1


def circle_method(n_teams: int) -> Tuple[List[List[int]], List[List[int]], List[List[int]]]:
    """
    Generate round-robin pairings using the circle method.
    """
    n_weeks = n_teams - 1
    n_periods = n_teams // 2

    base_a = []
    base_b = []
    team_match_idx = [[-1 for _ in range(n_weeks)] for _ in range(n_teams)]

    for w in range(1, n_weeks + 1):
        week_a = []
        week_b = []
        w_idx = w - 1

        for k in range(1, n_periods + 1):
            if k == 1:
                team_a = 0
                team_b = w
            else:
                team_a = wrap_1_to_m(w - (k - 1), n_weeks)
                team_b = wrap_1_to_m(w + (k - 1), n_weeks)

            k_idx = k - 1
            team_match_idx[team_a][w_idx] = k_idx
            team_match_idx[team_b][w_idx] = k_idx

            week_a.append(team_a)
            week_b.append(team_b)

        base_a.append(week_a)
        base_b.append(week_b)

    return base_a, base_b, team_match_idx