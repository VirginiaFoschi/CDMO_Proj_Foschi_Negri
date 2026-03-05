from typing import List, Dict
import z3

def extract_schedule(
    model: "z3.ModelRef",
    x, n_teams,
    A, B
) -> List[List[List[int]]]:
    """Build schedule[week][period] = [teamA, teamB]."""
    nW = n_teams - 1
    nP = n_teams // 2

    schedule = []
    for w in range(nW):
        row = [None] * nP
        for k in range(nP):
            for p in range(nP):
                if z3.is_true(model.evaluate(x[w][k][p])):
                    row[p] = [A[w][k], B[w][k]]
                    break
        schedule.append(row)
    return schedule