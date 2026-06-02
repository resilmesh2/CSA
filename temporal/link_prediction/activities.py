"""Activities for executing link prediction Cypher queries."""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict
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
                for stage_name, query in self._queries(params):
                    activity.heartbeat({"stage": stage_name, "status": "started"})
                    activity.logger.info("Starting link prediction stage %s", stage_name)
                    started = monotonic()
                    result = await session.run(query, query_params)
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
    def _queries(params: LinkPredictionParams) -> Sequence[tuple[str, str]]:
        queries = []
        if params.cleanup_existing:
            queries.extend(
                [
                    (
                        "drop_existing_model",
                        """
                        CALL gds.model.drop($model_name, false)
                        YIELD modelName
                        RETURN modelName
                        """,
                    ),
                    (
                        "drop_existing_pipeline",
                        """
                        CALL gds.pipeline.drop($pipeline_name, false)
                        YIELD pipelineName
                        RETURN pipelineName
                        """,
                    ),
                    (
                        "drop_existing_graph",
                        """
                        CALL gds.graph.drop($graph_name, false)
                        YIELD graphName
                        RETURN graphName
                        """,
                    ),
                    (
                        "delete_existing_direct_dependencies",
                        """
                        MATCH ()-[r:DIRECT_DEPENDENCY]->()
                        DELETE r
                        RETURN count(r) AS dependenciesDeleted
                        """,
                    ),
                ]
            )
        queries.extend([
            (
                "create_direct_dependencies",
                """
                MATCH (n1:Node)-[r1:IS_CONNECTED_TO]-(n2:Node)
                WITH n1, n2, count(r1) AS r1_count
                WHERE r1_count >= $r1_count_min
                MERGE (n1)-[:DIRECT_DEPENDENCY]->(n2)
                RETURN count(*) AS dependenciesProcessed
                """,
            ),
            (
                "mark_local_remote_dependencies",
                """
                MATCH (n1)-[r1:DIRECT_DEPENDENCY]->(n2)-[r2:DIRECT_DEPENDENCY]->(n3)
                WHERE EXISTS {
                  MATCH (n1)-[r3:IS_CONNECTED_TO]->(n2)-[r4:IS_CONNECTED_TO]->(n3)
                  WHERE r3.start <= r4.start <= r4.end <= r3.end
                  RETURN n1, n2, n3
                }
                SET r1.found = TRUE, r2.found = TRUE
                RETURN count(*) AS dependenciesMarked
                """,
            ),
            (
                "mark_remote_remote_dependencies",
                """
                MATCH (n1)-[r1:DIRECT_DEPENDENCY]->(n2)-[r2:DIRECT_DEPENDENCY]->(n3)
                WHERE EXISTS {
                  MATCH (n2)<-[r3:IS_CONNECTED_TO]-(n1)-[r4:IS_CONNECTED_TO]->(n3)
                  WHERE r3.end <= r4.start AND r4.start - r3.end <= $epsilon
                }
                SET r1.found = TRUE, r2.found = TRUE
                RETURN count(*) AS dependenciesMarked
                """,
            ),
            (
                "project_graph",
                """
                MATCH (n1)-[r:DIRECT_DEPENDENCY {found: TRUE}]->(n2)
                WITH gds.graph.project($graph_name, n1, n2, {
                    sourceNodeLabels: labels(n1),
                    targetNodeLabels: labels(n2),
                    relationshipType: 'POTENTIAL_DEPENDENCY'},
                    {undirectedRelationshipTypes: ['*']}) AS g
                RETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels
                """,
            ),
            (
                "create_pipeline",
                """
                CALL gds.beta.pipeline.linkPrediction.create($pipeline_name)
                YIELD name, nodePropertySteps, featureSteps, splitConfig, autoTuningConfig
                RETURN name, nodePropertySteps, featureSteps, splitConfig, autoTuningConfig
                """,
            ),
            (
                "add_node2vec_property",
                """
                CALL gds.beta.pipeline.linkPrediction.addNodeProperty($pipeline_name, 'Node2Vec', {
                  mutateProperty: 'embedding',
                  embeddingDimension: $embedding_dimension,
                  walkLength: $walk_length,
                  walksPerNode: $walks_per_node,
                  windowSize: $window_size,
                  negativeSamplingRate: $negative_sampling_rate,
                  iterations: $iterations
                })
                YIELD nodePropertySteps
                RETURN nodePropertySteps
                """,
            ),
            (
                "add_hadamard_feature",
                """
                CALL gds.beta.pipeline.linkPrediction.addFeature($pipeline_name, 'hadamard', {
                  nodeProperties: ['embedding']
                }) YIELD featureSteps
                RETURN featureSteps
                """,
            ),
            (
                "configure_split",
                """
                CALL gds.beta.pipeline.linkPrediction.configureSplit($pipeline_name, {
                  testFraction: $test_fraction,
                  trainFraction: $train_fraction,
                  validationFolds: $validation_folds
                })
                YIELD splitConfig
                RETURN splitConfig
                """,
            ),
            (
                "add_random_forest",
                """
                CALL gds.beta.pipeline.linkPrediction.addRandomForest($pipeline_name, {
                  numberOfDecisionTrees: $number_of_decision_trees,
                  maxDepth: $max_depth
                })
                YIELD parameterSpace
                RETURN parameterSpace
                """,
            ),
            (
                "configure_auto_tuning",
                """
                CALL gds.alpha.pipeline.linkPrediction.configureAutoTuning($pipeline_name, {
                  maxTrials: $max_trials
                })
                YIELD autoTuningConfig
                RETURN autoTuningConfig
                """,
            ),
            (
                "train",
                """
                CALL gds.beta.pipeline.linkPrediction.train($graph_name, {
                  pipeline: $pipeline_name,
                  modelName: $model_name,
                  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
                  targetRelationshipType: 'POTENTIAL_DEPENDENCY'
                }) YIELD modelInfo, modelSelectionStats
                RETURN
                  modelInfo.bestParameters AS winningModel,
                  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
                  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
                  modelInfo.metrics.AUCPR.test AS testScore,
                  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores
                """,
            ),
            (
                "predict",
                """
                CALL gds.beta.pipeline.linkPrediction.predict.mutate($graph_name, {
                  modelName: $model_name,
                  relationshipTypes: ['POTENTIAL_DEPENDENCY'],
                  mutateRelationshipType: 'PREDICTED_DEPENDENCY',
                  mutateProperty: 'probability',
                  topN: $top_n,
                  threshold: $threshold
                }) YIELD relationshipsWritten, samplingStats
                RETURN relationshipsWritten, samplingStats
                """,
            ),
            (
                "stream_predictions",
                """
                CALL gds.graph.relationshipProperty.stream(
                  $graph_name,
                  'probability',
                  ['PREDICTED_DEPENDENCY']
                )
                YIELD sourceNodeId, targetNodeId, relationshipType, propertyValue
                WITH
                  gds.util.asNode(sourceNodeId) AS sourceNode,
                  gds.util.asNode(targetNodeId) AS targetNode,
                  relationshipType,
                  propertyValue AS probability
                OPTIONAL MATCH (sourceNode)-[:IS_A]-(sourceHost:Host)
                OPTIONAL MATCH (sourceNode)-[:HAS_ASSIGNED]-(sourceIp:IP)
                WITH
                  sourceNode,
                  targetNode,
                  relationshipType,
                  probability,
                  collect(DISTINCT sourceHost.hostname) AS sourceHostnames,
                  collect(DISTINCT sourceIp.address) AS sourceIpAddresses
                OPTIONAL MATCH (targetNode)-[:IS_A]-(targetHost:Host)
                OPTIONAL MATCH (targetNode)-[:HAS_ASSIGNED]-(targetIp:IP)
                WITH
                  sourceNode,
                  targetNode,
                  relationshipType,
                  probability,
                  sourceHostnames,
                  sourceIpAddresses,
                  collect(DISTINCT targetHost.hostname) AS targetHostnames,
                  collect(DISTINCT targetIp.address) AS targetIpAddresses
                RETURN
                  elementId(sourceNode) AS sourceElementId,
                  coalesce(sourceHostnames[0], sourceIpAddresses[0], elementId(sourceNode)) AS sourceName,
                  sourceHostnames,
                  sourceIpAddresses,
                  labels(sourceNode) AS sourceLabels,
                  properties(sourceNode) AS sourceProperties,
                  elementId(targetNode) AS targetElementId,
                  coalesce(targetHostnames[0], targetIpAddresses[0], elementId(targetNode)) AS targetName,
                  targetHostnames,
                  targetIpAddresses,
                  labels(targetNode) AS targetLabels,
                  properties(targetNode) AS targetProperties,
                  relationshipType,
                  probability
                ORDER BY probability DESC
                LIMIT $prediction_limit
                """,
            ),
        ])
        return queries
