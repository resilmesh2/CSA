"""This module contains activities for criticality workflows using IP flow data."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Any
import httpx

from config import ISIMConfig
from temporalio import activity

class IPFlowCriticalityActivities:
    def __init__(self, isim_config: ISIMConfig) -> None:
        self.isim_config = isim_config

    @activity.defn
    async def compute_criticalities_flows(self) -> str:
        """
        This method computes degree and pagerank centralities based on IP flows.
        :return: texts from obtained responses from the REST API endpoints
        """
        async with httpx.AsyncClient() as client:
            first_response = await client.post(f"{self.isim_config.url}/nodes/ip_flows_degree")
            second_response = await client.post(f"{self.isim_config.url}/nodes/ip_flows_pagerank")
        return f"First response: {first_response.text}. Second response: {second_response.text}"

    @activity.defn
    async def compute_final_criticalities_flows(self) -> str:
        """
        This method calls ISIM's REST API endpoint that combines mission criticality
        and degree and pagerank centralities computed on IP flows.
        :return: text from obtained response from the REST API
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.isim_config.url}/nodes/combine_criticality_flows")
        return f"Response: {response.text}"

    def get_activities(self) -> Sequence[Callable[..., Awaitable[Any]]]:
        return [self.compute_criticalities_flows, self.compute_final_criticalities_flows]
