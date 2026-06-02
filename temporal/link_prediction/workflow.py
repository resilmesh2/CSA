"""Temporal workflow for link prediction pipeline experimentation."""

import asyncio
from datetime import timedelta
import json
import sys
import uuid

from config import AppConfig
from temporal.link_prediction.shared import LinkPredictionParams, LinkPredictionResult
from temporalio import workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy


@workflow.defn(name="LinkPredictionWorkflow")
class LinkPredictionWorkflow:
    @workflow.run
    async def run(self, params: LinkPredictionParams | None = None) -> LinkPredictionResult:
        """
        Run GDS link prediction pipeline with configurable experiment parameters.
        :param params: parameters for Cypher queries and GDS pipeline configuration
        :return: query results grouped by stage
        """
        from temporal.link_prediction.activities import LinkPredictionActivities

        params = params or LinkPredictionParams()
        return await workflow.execute_activity_method(
            LinkPredictionActivities.run_link_prediction_queries,
            params,
            retry_policy=RetryPolicy(maximum_attempts=1),
            heartbeat_timeout=timedelta(minutes=30),
            start_to_close_timeout=timedelta(hours=4),
        )


async def main() -> None:
    config = AppConfig.get()
    client = await Client.connect(config.temporal.url, namespace=config.temporal.namespace)
    workflow_id = uuid.uuid4().hex
    params = parse_params_arg()
    await client.start_workflow(
        LinkPredictionWorkflow.run,
        params,
        id=workflow_id,
        task_queue=config.temporal.csa_task_queue,
    )


def parse_params_arg() -> LinkPredictionParams:
    if len(sys.argv) <= 1:
        return LinkPredictionParams()

    return LinkPredictionParams(**json.loads(sys.argv[1]))


if __name__ == "__main__":
    asyncio.run(main())
