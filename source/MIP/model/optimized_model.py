from typing import List, Optional, Tuple
import pulp


def solve_mip_optimize(
    n_teams: int,
    timeout_s: int = 300,
    symm_break: bool = True,
    base_a: Optional[List[List[int]]] = None,
    base_b: Optional[List[List[int]]] = None,
    team_match_idx: Optional[List[List[int]]] = None,
    solver_type: str = "cbc",
    solver_verbose: bool = False,
) -> Tuple[bool, List[List[int]], Optional[int]]:

    # Basic checks
    if n_teams % 2 != 0:
        raise ValueError("Number of teams must be even.")

    if base_a is None or base_b is None or team_match_idx is None:
        raise ValueError("base_a, base_b, and team_match_idx must be provided.")

    n_weeks = n_teams - 1
    n_periods = n_teams // 2

    # Create model
    prob = pulp.LpProblem("STS_MIP_Optimize", pulp.LpMinimize)

    # x[w][k][p] = 1 if match k in week w is assigned to period p
    x = pulp.LpVariable.dicts(
        "x",
        (range(n_weeks), range(n_periods), range(1, n_periods + 1)),
        0,
        1,
        pulp.LpBinary,
    )

    # h[w][k] = 1 if base_a[w][k] plays at home
    h = pulp.LpVariable.dicts(
        "h",
        (range(n_weeks), range(n_periods)),
        0,
        1,
        pulp.LpBinary,
    )

    # --- Constraints ---

    # Each match must be assigned to exactly one period
    for w in range(n_weeks):
        for k in range(n_periods):
            prob += (
                pulp.lpSum(x[w][k][p] for p in range(1, n_periods + 1)) == 1
            )

    # Each period hosts exactly one match per week
    for w in range(n_weeks):
        for p in range(1, n_periods + 1):
            prob += (
                pulp.lpSum(x[w][k][p] for k in range(n_periods)) == 1
            )

    # Each team appears at most twice in the same period
    for t in range(n_teams):
        for p in range(1, n_periods + 1):
            prob += (
                pulp.lpSum(
                    x[w][team_match_idx[t][w]][p]
                    for w in range(n_weeks)
                ) <= 2
            )

    # --- Symmetry breaking ---
    if symm_break:

        # Fix periods of first week
        for k in range(n_periods):
            prob += (x[0][k][k + 1] == 1)

        # Fix orientation of first match
        prob += (h[0][0] == 1)

    # --- Home/Away balance ---

    # H[t] = number of home games of team t
    H = {}

    for t in range(n_teams):

        home_terms = []

        for w in range(n_weeks):

            k = team_match_idx[t][w]

            if base_a[w][k] == t:
                home_terms.append(h[w][k])

            elif base_b[w][k] == t:
                home_terms.append(1 - h[w][k])

        H[t] = pulp.lpSum(home_terms)

    # z = maximum imbalance
    # Lower bound = 1: since n_weeks = n-1 is always odd (n always even),
    # a perfectly balanced split is impossible, so max_imbalance >= 1.
    # Upper bound = n_weeks: worst case all games home or all away.
    z = pulp.LpVariable(
        "max_imbalance",
        lowBound=1,
        upBound=n_weeks,
        cat=pulp.LpInteger,
    )

    for t in range(n_teams):

        prob += (z >= 2 * H[t] - n_weeks)
        prob += (z >= n_weeks - 2 * H[t])

    # Objective
    prob += z

    # --- Solver selection ---
    solver_type = solver_type.lower()

    if solver_type == "cbc":
        solver = pulp.PULP_CBC_CMD(
            msg=solver_verbose,
            timeLimit=timeout_s,
        )

    elif solver_type == "highs":
        solver = pulp.HiGHS(
            msg=solver_verbose,
            timeLimit=timeout_s,
        )

    elif solver_type == "scip":
        solver = pulp.SCIP_PY(
            msg=solver_verbose,
            timeLimit=timeout_s,
        )

    else:
        raise ValueError("solver_type must be one of {'cbc','highs','scip'}")

    # Solve
    prob.solve(solver)

    status_name = pulp.LpStatus[prob.status]
    solved = status_name in {"Optimal", "Feasible"}

    if not solved:
        return False, [], None

    # Extract solution
    match_period_solution: List[List[int]] = []

    for w in range(n_weeks):

        week_solution = []

        for k in range(n_periods):

            assigned_period = None

            for p in range(1, n_periods + 1):

                val = pulp.value(x[w][k][p])

                if val is not None and val > 0.5:
                    assigned_period = p
                    break

            if assigned_period is None:
                raise RuntimeError(
                    f"No assigned period found for week {w}, match {k}"
                )

            week_solution.append(assigned_period)

        match_period_solution.append(week_solution)

    obj_value = int(round(pulp.value(z)))

    return True, match_period_solution, obj_value