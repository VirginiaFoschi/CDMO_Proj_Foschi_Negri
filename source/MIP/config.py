from dataclasses import dataclass
from typing import List


@dataclass
class ModelConfig:
    path: str
    opt: bool


@dataclass
class ExperimentConfig:
    nteams_values: List[int]
    timeout_s: int
    models: List[ModelConfig]
    sym_break: List[bool]

    def __post_init__(self):
        for n in self.nteams_values:
            if n % 2 != 0:
                raise ValueError(f"nTeams must be even, got {n}")
            if n < 4:
                raise ValueError(f"nTeams must be >= 4, got {n}")


DEFAULT_CONFIG = ExperimentConfig(
    nteams_values=[6, 8, 10, 12, 14, 16, 18, 20, 22],
    timeout_s=300,
    models=[
        ModelConfig(
            path="source/MIP/model/model.py",
            opt=False,
        ),
        ModelConfig(
            path="source/MIP/model/optimized_model.py",
            opt=True,
        ),
    ],
    sym_break=[False, True],
)