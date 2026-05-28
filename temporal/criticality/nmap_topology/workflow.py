"""This module contains a workflow for criticality computation."""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from datetime import timedelta
from typing import Any
from temporalio.client import Client
from config import AppConfig
from temporalio import workflow
from temporal.criticality.shared.activities import CriticalityActivities
from temporal.criticality.nmap_topology.activities import NmapCriticalityActivities
import uuid
from temporalio.common import RetryPolicy


@workflow.defn(name="NmapCriticalityWorkflow")
class NmapCriticalityWorkflow:
    @workflow.run
    async def run(self) -> None:
        """
        Run the criticality workflow consisting of three activities.
        :return:
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
            NmapCriticalityActivities.compute_criticalities_nmap,
            retry_policy=RetryPolicy(maximum_attempts=5),
            start_to_close_timeout=timedelta(minutes=60),
        )

        await workflow.execute_activity(
            NmapCriticalityActivities.compute_final_criticalities_nmap,
            retry_policy=RetryPolicy(maximum_attempts=5),
            start_to_close_timeout=timedelta(minutes=60),
        )

    @classmethod
    def get_activities(cls) -> Sequence[Callable[..., Awaitable[Any]]]:
        config = AppConfig.get()
        shared_activities = CriticalityActivities(config.isim)
        nmap_activities = NmapCriticalityActivities(config.isim)
        return [*shared_activities.get_activities(), *nmap_activities.get_activities()]


async def main() -> None:
    config = AppConfig.get()
    client = await Client.connect(config.temporal.url, namespace=config.temporal.namespace)
    workflow_id = uuid.uuid4().hex
    await client.start_workflow(
        NmapCriticalityWorkflow.run,
        args=(),
        id=workflow_id,
        task_queue=config.temporal.csa_task_queue,
    )


if __name__ == "__main__":
    asyncio.run(main())
