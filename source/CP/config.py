from typing import List

class ExperimentConfig:
    """Configuration for running experiments."""
    nteams_values: List[int]
    solvers: List[str]
    timeout_seconds: int
    models: List[str]

    def __init__(
        self,
        nteams_values: List[int],
        solvers: List[str],
        timeout_ms: int,
        models: List[str]
    ):
        self.nteams_values = nteams_values
        self.solvers = solvers
        self.timeout_ms = timeout_ms
        self.models = models
    
    def __post_init__(self):
        """Validate configuration."""
        for n in self.nteams_values:
            if n % 2 != 0:
                raise ValueError(f"nTeams must be even, got {n}")
            if n < 4:
                raise ValueError(f"nTeams must be >= 4, got {n}")


# Default configuration
DEFAULT_CONFIG = ExperimentConfig(
    nteams_values=[6, 8, 10, 12, 14, 16, 18],
    solvers=['chuffed'],
    timeout_ms=300000,
    models=['model/model.mzn', 'model/optimized_model.mzn']
)


# Solver display names
SOLVER_NAMES = {
    'gecode': 'Gecode',
    'chuffed': 'Chuffed'
}