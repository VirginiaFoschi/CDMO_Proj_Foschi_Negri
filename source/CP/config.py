from dataclasses import dataclass
from typing import List

@dataclass
class ModelConfig:
    name: str
    path: str
    opt: bool

@dataclass
class ExperimentConfig:
    """Configuration for running experiments."""
    nteams_values: List[int]
    solvers: List[str]
    timeout_s: int
    models: List[str]
    sym_break: List[bool]

    def __post_init__(self):
        """Validate configuration."""
        for n in self.nteams_values:
            if n % 2 != 0:
                raise ValueError(f"nTeams must be even, got {n}")
            if n < 4:
                raise ValueError(f"nTeams must be >= 4, got {n}")

MODELS = {
    "decision": ModelConfig(
            name = "decision",
            path="source/CP/model/model.mzn",
            opt=False
        ),
    "optimized": ModelConfig(
            name = "optimized",
            path="source/CP/model/optimized_model.mzn",
            opt=True
        ),
    "optimized_dwd_luby": ModelConfig(
            name = "optimized_dwd_luby",
            path="source/CP/model/optimized_model_dwd_luby.mzn",
            opt=True
    )
}

# Default configuration
DEFAULT_CONFIG = ExperimentConfig(
    nteams_values=[6,8,10,12,14,16,18,20,22],
    solvers=["gecode", "chuffed"],
    timeout_s=300,
    models=["decision", "optimized", "optimized_dwd_luby"],
    sym_break = [False, True]
)


# Solver display names
SOLVER_NAMES = {
    'gecode': 'Gecode',
    'chuffed': 'Chuffed'
}