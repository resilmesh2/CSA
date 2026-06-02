"""Activities for executing link prediction Cypher queries."""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass
from functools import cached_property
from importlib.resources import files
from time import monotonic
from typing import Any

from config import Neo4jConfig
from neo4j import AsyncGraphDatabase
from temporal.link_prediction.shared import (
    LinkPredictionParams,
    LinkPredictionResult,
    LinkPredictionStageResult,
)
from temporalio import activity


@dataclass(frozen=True)
class LinkPredictionQuery:
    stage: str
    file_name: str

    @cached_property
    def cypher(self) -> str:
        return (
            files("temporal.link_prediction.queries")
            .joinpath(self.file_name)
            .read_text()
        )


class LinkPredictionActivities:
    """Activities used by the link prediction workflow."""

    def __init__(self, neo4j_config: Neo4jConfig) -> None:
        self.neo4j_config = neo4j_config

    @activity.defn
    async def run_link_prediction_queries(
        self, params: LinkPredictionParams
    ) -> LinkPredictionResult:
        """
        Execute link prediction Cypher queries in the required order.
        :param params: parameters used by Cypher queries and GDS pipeline configuration
        :return: records returned by each query stage
        """
        params.validate()
        driver = AsyncGraphDatabase.driver(
            self.neo4j_config.bolt,
            auth=(self.neo4j_config.user, self.neo4j_config.password),
        )
        try:
            async with driver.session() as session:
                query_params = asdict(params)
                stages = []
                for query in self._queries(params):
                    stage_name = query.stage
                    activity.heartbeat({"stage": stage_name, "status": "started"})
                    activity.logger.info("Starting link prediction stage %s", stage_name)
                    started = monotonic()
                    result = await session.run(query.cypher, query_params)
                    records = [record.data() async for record in result]
                    duration_seconds = monotonic() - started
                    activity.heartbeat(
                        {
                            "stage": stage_name,
                            "status": "completed",
                            "duration_seconds": duration_seconds,
                            "record_count": len(records),
                        }
                    )
                    activity.logger.info(
                        "Completed link prediction stage %s in %.3fs with %d records",
                        stage_name,
                        duration_seconds,
                        len(records),
                    )
                    stages.append(
                        LinkPredictionStageResult(
                            stage=stage_name,
                            records=records,
                            duration_seconds=duration_seconds,
                            record_count=len(records),
                        )
                    )
                return LinkPredictionResult(stages=stages)
        finally:
            await driver.close()

    def get_activities(self) -> Sequence[Callable[..., Awaitable[Any]]]:
        return [self.run_link_prediction_queries]

    @staticmethod
    def _queries(params: LinkPredictionParams) -> Sequence[LinkPredictionQuery]:
        if params.cleanup_existing:
            return [
                *LinkPredictionActivities._cleanup_queries(),
                *LinkPredictionActivities._pipeline_queries(),
            ]

        return LinkPredictionActivities._pipeline_queries()

    @staticmethod
    def _cleanup_queries() -> list[LinkPredictionQuery]:
        return [
            LinkPredictionQuery("drop_existing_model", "drop_existing_model.cypher"),
            LinkPredictionQuery("drop_existing_pipeline", "drop_existing_pipeline.cypher"),
            LinkPredictionQuery("drop_existing_graph", "drop_existing_graph.cypher"),
            LinkPredictionQuery(
                "delete_existing_direct_dependencies",
                "delete_existing_direct_dependencies.cypher",
            ),
        ]

    @staticmethod
    def _pipeline_queries() -> list[LinkPredictionQuery]:
        return [
            LinkPredictionQuery(
                "create_direct_dependencies",
                "create_direct_dependencies.cypher",
            ),
            LinkPredictionQuery(
                "mark_local_remote_dependencies",
                "mark_local_remote_dependencies.cypher",
            ),
            LinkPredictionQuery(
                "mark_remote_remote_dependencies",
                "mark_remote_remote_dependencies.cypher",
            ),
            LinkPredictionQuery("project_graph", "project_graph.cypher"),
            LinkPredictionQuery("create_pipeline", "create_pipeline.cypher"),
            LinkPredictionQuery("add_node2vec_property", "add_node2vec_property.cypher"),
            LinkPredictionQuery("add_hadamard_feature", "add_hadamard_feature.cypher"),
            LinkPredictionQuery("configure_split", "configure_split.cypher"),
            LinkPredictionQuery("add_random_forest", "add_random_forest.cypher"),
            LinkPredictionQuery("configure_auto_tuning", "configure_auto_tuning.cypher"),
            LinkPredictionQuery("train", "train.cypher"),
            LinkPredictionQuery("predict", "predict.cypher"),
            LinkPredictionQuery("stream_predictions", "stream_predictions.cypher"),
        ]
