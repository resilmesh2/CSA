"""This module contains a workflow for criticality computation using IP flow data."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from datetime import timedelta
from typing import Any
from temporalio.client import Client
from config import AppConfig
from temporalio import workflow
from temporal.criticality.shared.activities import CriticalityActivities
from temporal.criticality.ip_flow.activities import IPFlowCriticalityActivities
import uuid
from temporalio.common import RetryPolicy


@workflow.defn(name="IPFlowCriticalityWorkflow")
class IPFlowCriticalityWorkflow:
    @workflow.run
    async def run(self) -> None:
        """
        Run IPFlowCriticalityWorkflow that computes criticality of network nodes based on IP flow data.
        :return: None
        """
        criticality_results = await workflow.execute_activity(
            CriticalityActivities.compute_mission_criticalities,
            retry_policy=RetryPolicy(maximum_attempts=5),
            start_to_close_timeout=timedelta(minutes=60),
        )

        await workflow.execute_activity(
            CriticalityActivities.store_mission_criticalities,
            criticality_results,
            retry_policy=RetryPolicy(maximum_attempts=5),
            start_to_close_timeout=timedelta(minutes=60),
        )

        await workflow.execute_activity(
            IPFlowCriticalityActivities.compute_criticalities_flows,
            retry_policy=RetryPolicy(maximum_attempts=5),
            start_to_close_timeout=timedelta(minutes=60),
        )

        await workflow.execute_activity(
            IPFlowCriticalityActivities.compute_final_criticalities_flows,
            retry_policy=RetryPolicy(maximum_attempts=5),
            start_to_close_timeout=timedelta(minutes=60),
        )

    @classmethod
    def get_activities(cls) -> Sequence[Callable[..., Awaitable[Any]]]:
        config = AppConfig.get()
        shared_activities = CriticalityActivities(config.isim)
        ip_flow_activities = IPFlowCriticalityActivities(config.isim)
        return [*shared_activities.get_activities(), *ip_flow_activities.get_activities()]


async def main() -> None:
    config = AppConfig.get()
    client = await Client.connect(config.temporal.url, namespace=config.temporal.namespace)
    workflow_id = uuid.uuid4().hex
    await client.start_workflow(
        IPFlowCriticalityWorkflow.run,
        args=(),
        id=workflow_id,
        task_queue=config.temporal.csa_task_queue,
    )


if __name__ == "__main__":
    asyncio.run(main())
