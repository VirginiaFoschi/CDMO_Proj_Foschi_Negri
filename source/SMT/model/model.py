import time
from typing import Dict, List, Optional
from circle_method import circle_method
import z3

def lex_lesseq(a, b):
    n = len(a)
    clauses = []
    equal_prefix = z3.BoolVal(True)

    for i in range(n):
        clauses.append(z3.And(equal_prefix, a[i] < b[i]))
        equal_prefix = z3.And(equal_prefix, a[i] == b[i])

    clauses.append(equal_prefix)  # allow equality
    return z3.Or(*clauses)

# ================================================================
#  Model builder
# ================================================================

def build_model(n_teams: int, A, B, symmetry_breaking=True):
    """
    Build Z3 model with boolean encoding.
    """
    nW = n_teams - 1
    nP = n_teams // 2

    solver = z3.Solver()
    solver.set("sat.phase", "caching")

    # ── Boolean decision variables ──────────────────────────
    x = [
        [
            [z3.Bool(f"x_{w+1}_{k+1}_{p+1}") for p in range(nP)]
            for k in range(nP)
        ]
        for w in range(nW)
    ]

    # ── Exactly-one period per match ────────────────────────
    for w in range(nW):
        for k in range(nP):
            solver.add(z3.PbEq([(x[w][k][p], 1) for p in range(nP)], 1))

    # ── Exactly-one match per period per week ───────────────
    for w in range(nW):
        for p in range(nP):
            solver.add(z3.PbEq([(x[w][k][p], 1) for k in range(nP)], 1))

    # ── Precompute team slots ───────────────────────────────
    team_slots = {t: [] for t in range(n_teams)}
    for w in range(nW):
        for k in range(nP):
            team_slots[A[w][k]].append((w, k))
            team_slots[B[w][k]].append((w, k))

    # ── C2: at most 2 per team per period ───────────────────
    for t in range(n_teams):
        slots = team_slots[t]
        if len(slots) <= 2:
            continue
        for p in range(nP):
            bools = [x[w][k][p] for w, k in slots]
            solver.add(z3.AtMost(*bools, 2))

            # IMPLIED: at least 1 per period (pigeonhole)
            # nWeeks matches into nPeriods slots with max 2 each
            # capacity = 2*nP = nTeams, need = nWeeks = nTeams-1
            # → every period must have at least 1
            solver.add(z3.AtLeast(*bools, 1))

    # ── Symmetry breaking ───────────────────────────────────
    if symmetry_breaking:
        for k in range(nP):
            solver.add(x[0][k][k])

    return solver, x