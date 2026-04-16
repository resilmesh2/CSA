"""This module contains the main procedure for Temporal worker."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from config import AppConfig
from temporal.criticality.workflow import CriticalityWorkflow
from temporal.criticality.ip_flow_workflow import IPFlowCriticalityWorkflow


async def main() -> None:
    """
    This procedure creates a worker for CSA component in Temporal.
    :return:
    """
    config = AppConfig.get()
    client = await Client.connect(config.temporal.url, namespace=config.temporal.namespace)
    workflows = [CriticalityWorkflow, IPFlowCriticalityWorkflow]
    activities = CriticalityWorkflow.get_activities()
    workflow_runner = SandboxedWorkflowRunner(
        restrictions=SandboxRestrictions.default.with_passthrough_modules(
            "temporal.criticality",
            "config"
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
