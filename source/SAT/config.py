from dataclasses import dataclass, field
from typing import List


# PySAT solver names
AVAILABLE_SOLVERS = [
    "glucose3",
    "glucose4",
    "minisat22",
    "lingeling",
    "cadical195",
    "maplesat",
    "mergesat3",
]


@dataclass
class ModelConfig:
    path: str
    opt:  bool
    z3:   bool = False   # True -> use Z3 backend instead of PySAT


@dataclass
class ExperimentConfig:
    nteams_values: List[int]
    timeout_s:     int
    models:        List[ModelConfig]
    sym_break:     List[bool]
    solvers:       List[str] = field(default_factory=lambda: ["glucose4", "cadical195", "minisat22"])

    def __post_init__(self):
        for n in self.nteams_values:
            if n % 2 != 0:
                raise ValueError(f"nTeams must be even, got {n}")
            if n < 4:
                raise ValueError(f"nTeams must be >= 4, got {n}")
        for s in self.solvers:
            if s not in AVAILABLE_SOLVERS:
                raise ValueError(f"Unknown solver '{s}'. Choose from: {AVAILABLE_SOLVERS}")


DEFAULT_CONFIG = ExperimentConfig(
    nteams_values=[6, 8, 10, 12, 14, 16, 18, 20, 22],
    timeout_s=300,
    models=[
        ModelConfig(path="source/SAT/model/model.py",              opt=False, z3=False),
        ModelConfig(path="source/SAT/model/optimized_model.py",    opt=True,  z3=False),
        ModelConfig(path="source/SAT/model/z3_model.py",           opt=False, z3=True),
        ModelConfig(path="source/SAT/model/z3_optimized_model.py", opt=True,  z3=True),
    ],
    sym_break=[False, True],
    solvers=["glucose4", "cadical195", "minisat22"],
)
