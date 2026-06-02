"""Shared data structures for link prediction workflows."""

from dataclasses import dataclass
from typing import Any


@dataclass
class LinkPredictionParams:
    """Parameters for link prediction Cypher queries and GDS pipeline tuning."""

    cleanup_existing: bool = True
    r1_count_min: int = 10
    epsilon: int = 1000
    graph_name: str = "linkPredictionGraph"
    pipeline_name: str = "link-prediction"
    model_name: str = "link-prediction-model"
    embedding_dimension: int = 64
    walk_length: int = 5
    walks_per_node: int = 10
    window_size: int = 4
    negative_sampling_rate: int = 1
    iterations: int = 10
    test_fraction: float = 0.25
    train_fraction: float = 0.6
    validation_folds: int = 5
    number_of_decision_trees: int = 50
    max_depth: int = 30
    max_trials: int = 2
    top_n: int = 100
    threshold: float = 0.5
    prediction_limit: int = 500

    def validate(self) -> None:
        if self.walk_length < 2:
            raise ValueError("walk_length must be >= 2")
        if self.window_size < 2:
            raise ValueError("window_size must be >= 2")
        if self.walks_per_node < 1:
            raise ValueError("walks_per_node must be >= 1")
        if self.iterations < 1:
            raise ValueError("iterations must be >= 1")
        if self.embedding_dimension < 1:
            raise ValueError("embedding_dimension must be >= 1")
        if self.validation_folds < 2:
            raise ValueError("validation_folds must be >= 2")
        if self.number_of_decision_trees < 1:
            raise ValueError("number_of_decision_trees must be >= 1")
        if self.max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        if self.max_trials < 1:
            raise ValueError("max_trials must be >= 1")


@dataclass
class LinkPredictionStageResult:
    stage: str
    records: list[dict[str, Any]]
    duration_seconds: float
    record_count: int


@dataclass
class LinkPredictionResult:
    stages: list[LinkPredictionStageResult]
