"""Activities for executing link prediction Cypher queries."""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import cached_property
from importlib.resources import files
from time import monotonic
from typing import Any

from config import Neo4jConfig
from neo4j import AsyncGraphDatabase
from temporal.link_prediction.shared import (
    LinkPredictionInputValidationResult,
    LinkPredictionParams,
    LinkPredictionResult,
    LinkPredictionStageResult,
    extract_link_prediction_overrides,
    merge_link_prediction_params,
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

    def __init__(
        self,
        neo4j_config: Neo4jConfig,
        link_prediction_config: LinkPredictionParams,
    ) -> None:
        self.neo4j_config = neo4j_config
        self.link_prediction_config = link_prediction_config

    @activity.defn
    async def validate_link_prediction_input(
        self,
        input_: dict[str, Any],
    ) -> LinkPredictionInputValidationResult:
        """
        Validate and normalize workflow input overriding configured defaults.
        :param input_: mapping compatible with LinkPredictionParams
        :return: normalized override values and effective workflow flags
        """
        params_override = extract_link_prediction_overrides(input_)
        params = merge_link_prediction_params(
            self.link_prediction_config,
            params_override,
        )
        return LinkPredictionInputValidationResult(
            params_override=params_override,
            cleanup_existing=params.cleanup_existing,
        )

    @activity.defn
    async def run_link_prediction_cleanup_queries(
        self, params_override: dict[str, Any] | None
    ) -> LinkPredictionResult:
        """
        Execute cleanup Cypher queries when configured.
        :param params_override: optional workflow input overriding configured defaults
        :return: records returned by each query stage
        """
        params = merge_link_prediction_params(
            self.link_prediction_config,
            params_override,
        )
        return await self._run_queries(self._cleanup_queries(), params)

    @activity.defn
    async def run_link_prediction_pipeline_queries(
        self, params_override: dict[str, Any] | None
    ) -> LinkPredictionResult:
        """
        Execute link prediction pipeline Cypher queries.
        :param params_override: optional workflow input overriding configured defaults
        :return: records returned by each query stage
        """
        params = merge_link_prediction_params(
            self.link_prediction_config,
            params_override,
        )
        return await self._run_queries(self._pipeline_queries(), params)

    def get_activities(self) -> Sequence[Callable[..., Awaitable[Any]]]:
        return [
            self.validate_link_prediction_input,
            self.run_link_prediction_cleanup_queries,
            self.run_link_prediction_pipeline_queries,
        ]

    async def _run_queries(
        self,
        queries: Sequence[LinkPredictionQuery],
        params: LinkPredictionParams,
    ) -> LinkPredictionResult:
        driver = AsyncGraphDatabase.driver(
            self.neo4j_config.bolt,
            auth=(self.neo4j_config.user, self.neo4j_config.password),
        )
        try:
            async with driver.session() as session:
                query_params = params.model_dump()
                stages = []
                for query in queries:
                    stage_name = query.stage
                    activity.heartbeat({"stage": stage_name, "status": "started"})
                    activity.logger.info(
                        "Starting link prediction stage %s", stage_name
                    )
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

    @staticmethod
    def _cleanup_queries() -> list[LinkPredictionQuery]:
        return [
            LinkPredictionQuery("drop_existing_model", "drop_existing_model.cypher"),
            LinkPredictionQuery(
                "drop_existing_pipeline", "drop_existing_pipeline.cypher"
            ),
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
            LinkPredictionQuery(
                "add_node2vec_property", "add_node2vec_property.cypher"
            ),
            LinkPredictionQuery("add_hadamard_feature", "add_hadamard_feature.cypher"),
            LinkPredictionQuery("configure_split", "configure_split.cypher"),
            LinkPredictionQuery("add_random_forest", "add_random_forest.cypher"),
            LinkPredictionQuery(
                "configure_auto_tuning", "configure_auto_tuning.cypher"
            ),
            LinkPredictionQuery("train", "train.cypher"),
            LinkPredictionQuery("predict", "predict.cypher"),
            LinkPredictionQuery("stream_predictions", "stream_predictions.cypher"),
        ]
