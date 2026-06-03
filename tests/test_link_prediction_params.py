import pytest
from pydantic import ValidationError

from temporal.link_prediction.activities import LinkPredictionActivities
from temporal.link_prediction.shared import (
    LinkPredictionParams,
    extract_link_prediction_overrides,
    merge_link_prediction_params,
)


def test_merge_replaces_only_provided_fields(
    link_prediction_config: LinkPredictionParams,
) -> None:
    merged = merge_link_prediction_params(
        link_prediction_config,
        {"top_n": 50},
    )

    assert merged.top_n == 50
    assert merged.r1_count_min == link_prediction_config.r1_count_min
    assert merged.threshold == link_prediction_config.threshold
    assert merged.prediction_limit == link_prediction_config.prediction_limit


def test_merge_ignores_none_values(
    link_prediction_config: LinkPredictionParams,
) -> None:
    merged = merge_link_prediction_params(
        link_prediction_config,
        {"threshold": 0.5},
    )

    assert merged.top_n == link_prediction_config.top_n
    assert merged.threshold == 0.5


def test_merge_none_override_returns_base(
    link_prediction_config: LinkPredictionParams,
) -> None:
    merged = merge_link_prediction_params(link_prediction_config, None)

    assert merged is link_prediction_config


def test_validate_rejects_missing_config_params() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        LinkPredictionParams.model_validate({})


def test_validate_accepts_config_params(
    link_prediction_config: LinkPredictionParams,
) -> None:
    params = LinkPredictionParams.model_validate(link_prediction_config.model_dump())

    assert params == link_prediction_config


def test_extract_overrides_uses_only_provided_fields() -> None:
    overrides = extract_link_prediction_overrides({"top_n": 50})

    assert overrides == {"top_n": 50}


def test_extract_overrides_ignores_null_values() -> None:
    overrides = extract_link_prediction_overrides({"top_n": None, "threshold": 0.5})

    assert overrides == {"threshold": 0.5}


def test_extract_overrides_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="unknown"):
        extract_link_prediction_overrides({"unknown": None})


def test_query_groups_are_separate() -> None:
    cleanup_queries = LinkPredictionActivities._cleanup_queries()
    pipeline_queries = LinkPredictionActivities._pipeline_queries()

    assert [query.stage for query in cleanup_queries] == [
        "drop_existing_model",
        "drop_existing_pipeline",
        "drop_existing_graph",
        "delete_existing_direct_dependencies",
    ]
    assert pipeline_queries[0].stage == "create_direct_dependencies"
    assert pipeline_queries[-1].stage == "stream_predictions"
    assert {query.stage for query in cleanup_queries}.isdisjoint(
        {query.stage for query in pipeline_queries}
    )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("test_fraction", 0),
        ("test_fraction", 1),
        ("train_fraction", 0),
        ("train_fraction", 1),
    ],
)
def test_validate_rejects_invalid_docs_backed_gds_params(
    field_name: str,
    invalid_value: int,
    link_prediction_config: LinkPredictionParams,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        merge_link_prediction_params(
            link_prediction_config,
            {field_name: invalid_value},
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("walk_length", 1),
        ("window_size", 1),
    ],
)
def test_validate_rejects_invalid_runtime_backed_gds_params(
    field_name: str,
    invalid_value: int,
    link_prediction_config: LinkPredictionParams,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        merge_link_prediction_params(
            link_prediction_config,
            {field_name: invalid_value},
        )


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("walks_per_node", 0),
        ("iterations", 0),
        ("embedding_dimension", 0),
        ("validation_folds", 1),
        ("number_of_decision_trees", 0),
        ("max_depth", 0),
        ("max_trials", 0),
        ("top_n", 0),
        ("threshold", -0.1),
        ("threshold", 1.1),
        ("prediction_limit", 0),
    ],
)
def test_validate_rejects_invalid_defensive_params(
    field_name: str,
    invalid_value: int | float,
    link_prediction_config: LinkPredictionParams,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        merge_link_prediction_params(
            link_prediction_config,
            {field_name: invalid_value},
        )


@pytest.mark.asyncio
async def test_validate_activity_returns_typed_override(
    link_prediction_activities: LinkPredictionActivities,
) -> None:
    result = await link_prediction_activities.validate_link_prediction_input(
        {"top_n": 50},
    )

    assert result.params_override == {"top_n": 50}
    assert result.cleanup_existing is True


@pytest.mark.asyncio
async def test_validate_activity_returns_effective_cleanup_flag(
    link_prediction_activities: LinkPredictionActivities,
) -> None:
    result = await link_prediction_activities.validate_link_prediction_input(
        {"cleanup_existing": False},
    )

    assert result.params_override == {"cleanup_existing": False}
    assert result.cleanup_existing is False


@pytest.mark.asyncio
async def test_validate_activity_rejects_invalid_effective_params(
    link_prediction_activities: LinkPredictionActivities,
) -> None:
    with pytest.raises(ValidationError, match="walk_length"):
        await link_prediction_activities.validate_link_prediction_input(
            {"walk_length": 1},
        )
