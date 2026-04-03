from dataclasses import dataclass
from typing import List

@dataclass
class ModelConfig:
    path: str
    opt: bool

@dataclass
class ExperimentConfig:
    """Configuration for running experiments."""
    nteams_values: List[int]
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
            path="source/SMT/model/model.mzn",
            opt=False
        ),
    "optimized": 
        ModelConfig(
            path="source/SMT/model/optimized_model.mzn",
            opt=True
        )
}

# Default configuration
DEFAULT_CONFIG = ExperimentConfig(
    nteams_values=[6,8,10,12,14,16,18,20,22],
    timeout_s=300,
    models=["decision", "optimized"],
    sym_break = [False, True]
)