"""This module contains the main procedure for Temporal worker."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

from config import AppConfig
from temporal.criticality.nmap_topology.activities import NmapCriticalityActivities
from temporal.criticality.nmap_topology.workflow import NmapCriticalityWorkflow
from temporal.criticality.ip_flow.activities import IPFlowCriticalityActivities
from temporal.criticality.ip_flow.workflow import IPFlowCriticalityWorkflow
from temporal.link_prediction.activities import LinkPredictionActivities
from temporal.link_prediction.workflow import LinkPredictionWorkflow
from temporal.criticality.shared.activities import CriticalityActivities


async def main() -> None:
    """
    This procedure creates a worker for CSA component in Temporal.
    :return:
    """
    config = AppConfig.get()
    client = await Client.connect(
        config.temporal.url, namespace=config.temporal.namespace
    )
    workflows = [
        NmapCriticalityWorkflow,
        IPFlowCriticalityWorkflow,
        LinkPredictionWorkflow,
    ]
    activities = [
        *NmapCriticalityActivities(config.isim).get_activities(),
        *IPFlowCriticalityActivities(config.isim).get_activities(),
        *CriticalityActivities(config.isim).get_activities(),
        *LinkPredictionActivities(
            config.neo4j,
            config.link_prediction,
        ).get_activities(),
    ]
    workflow_runner = SandboxedWorkflowRunner(
        restrictions=SandboxRestrictions.default.with_passthrough_modules(
            "temporal.criticality", "temporal.link_prediction", "config"
        )
    )

    worker = Worker(
        client=client,
        task_queue=config.temporal.csa_task_queue,
        workflows=workflows,
        activities=activities,
        workflow_runner=workflow_runner,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
