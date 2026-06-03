"""Shared data structures for link prediction workflows."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LinkPredictionParams(BaseModel):
    """Parameters for link prediction Cypher queries and GDS pipeline tuning."""

    model_config = ConfigDict(extra="forbid")

    # Workflow/domain constraints, not GDS API constraints.
    cleanup_existing: bool
    r1_count_min: int = Field(ge=1)
    epsilon: int = Field(ge=0)
    graph_name: str
    pipeline_name: str
    model_name: str

    # Node2Vec constraints are defensive, except walk/window minimums observed from GDS.
    embedding_dimension: int = Field(ge=1)
    walk_length: int = Field(ge=2)
    walks_per_node: int = Field(ge=1)
    window_size: int = Field(ge=2)
    negative_sampling_rate: int = Field(ge=1)
    iterations: int = Field(ge=1)

    # GDS docs specify split fractions must be in (0, 1).
    test_fraction: float = Field(gt=0, lt=1)
    train_fraction: float = Field(gt=0, lt=1)

    # Positive integer checks below are defensive unless noted in GDS docs/runtime errors.
    validation_folds: int = Field(ge=2)
    number_of_decision_trees: int = Field(ge=1)
    max_depth: int = Field(ge=1)
    max_trials: int = Field(ge=1)
    top_n: int = Field(ge=1)

    # Threshold is a predicted probability; prediction_limit is our result LIMIT.
    threshold: float = Field(ge=0, le=1)
    prediction_limit: int = Field(ge=1)


def extract_link_prediction_overrides(input_: dict[str, Any]) -> dict[str, Any]:
    unknown_fields = set(input_) - set(LinkPredictionParams.model_fields)
    if unknown_fields:
        raise ValueError(
            "Unknown link prediction params: " + ", ".join(sorted(unknown_fields))
        )

    return {key: value for key, value in input_.items() if value is not None}


def merge_link_prediction_params(
    base: LinkPredictionParams,
    override: dict[str, Any] | None,
) -> LinkPredictionParams:
    if override is None:
        return base

    return LinkPredictionParams.model_validate(
        {
            **base.model_dump(),
            **override,
        }
    )


@dataclass
class LinkPredictionStageResult:
    stage: str
    records: list[dict[str, Any]]
    duration_seconds: float
    record_count: int


@dataclass
class LinkPredictionResult:
    stages: list[LinkPredictionStageResult]
