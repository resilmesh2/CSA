import pytest

from config import Neo4jConfig
from temporal.link_prediction.activities import LinkPredictionActivities
from temporal.link_prediction.shared import LinkPredictionParams


@pytest.fixture
def neo4j_config() -> Neo4jConfig:
    return Neo4jConfig(
        bolt="bolt://unused:7687",
        user="neo4j",
        password="password",
    )


@pytest.fixture
def link_prediction_config() -> LinkPredictionParams:
    return LinkPredictionParams(
        cleanup_existing=True,
        r1_count_min=42,
        epsilon=1000,
        graph_name="linkPredictionGraph",
        pipeline_name="link-prediction",
        model_name="link-prediction-model",
        embedding_dimension=64,
        walk_length=5,
        walks_per_node=10,
        window_size=4,
        negative_sampling_rate=1,
        iterations=10,
        test_fraction=0.25,
        train_fraction=0.6,
        validation_folds=5,
        number_of_decision_trees=50,
        max_depth=30,
        max_trials=2,
        top_n=100,
        threshold=0.8,
        prediction_limit=500,
    )


@pytest.fixture
def link_prediction_activities(
    neo4j_config: Neo4jConfig,
    link_prediction_config: LinkPredictionParams,
) -> LinkPredictionActivities:
    return LinkPredictionActivities(neo4j_config, link_prediction_config)
