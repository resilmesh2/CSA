"""Temporal workflow for link prediction pipeline experimentation."""

import asyncio
from datetime import timedelta
import json
import sys
import uuid
from typing import Any

from config import AppConfig
from temporal.link_prediction.shared import LinkPredictionResult
from temporalio import workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporal.link_prediction.activities import LinkPredictionActivities


@workflow.defn(name="LinkPredictionWorkflow")
class LinkPredictionWorkflow:
    @workflow.run
    async def run(
        self,
        input_: dict[str, Any] | None = None,
    ) -> LinkPredictionResult:
        """
        Run GDS link prediction pipeline with configurable experiment parameters.
        :param input_: optional mapping overriding configured link prediction parameters
        :return: query results grouped by stage
        """
        validation_result = await workflow.execute_activity_method(
            LinkPredictionActivities.validate_link_prediction_input,
            input_ or {},
            retry_policy=RetryPolicy(maximum_attempts=1),
            start_to_close_timeout=timedelta(minutes=5),
        )
        params_override = validation_result.params_override

        cleanup_stages = []
        if validation_result.cleanup_existing:
            cleanup_result = await workflow.execute_activity_method(
                LinkPredictionActivities.run_link_prediction_cleanup_queries,
                params_override,
                retry_policy=RetryPolicy(maximum_attempts=1),
                heartbeat_timeout=timedelta(minutes=15),
                start_to_close_timeout=timedelta(minutes=30),
            )
            cleanup_stages = cleanup_result.stages

        pipeline_result = await workflow.execute_activity_method(
            LinkPredictionActivities.run_link_prediction_pipeline_queries,
            params_override,
            retry_policy=RetryPolicy(maximum_attempts=1),
            heartbeat_timeout=timedelta(minutes=30),
            start_to_close_timeout=timedelta(hours=4),
        )

        return LinkPredictionResult(
            stages=[
                *cleanup_stages,
                *pipeline_result.stages,
            ]
        )


async def main() -> None:
    config = AppConfig.get()
    client = await Client.connect(
        config.temporal.url, namespace=config.temporal.namespace
    )
    workflow_id = uuid.uuid4().hex
    params = parse_params_arg()
    await client.start_workflow(
        LinkPredictionWorkflow.run,
        params,
        id=workflow_id,
        task_queue=config.temporal.csa_task_queue,
    )


def parse_params_arg() -> dict[str, Any] | None:
    if len(sys.argv) <= 1:
        return None

    return json.loads(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())
