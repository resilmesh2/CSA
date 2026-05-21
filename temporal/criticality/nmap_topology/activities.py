"""This module contains activities that are used solely by criticality workflows for data
from Nmap topology scan."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Any
import httpx

from config import ISIMConfig
from temporalio import activity

class NmapCriticalityActivities:
    def __init__(self, isim_config: ISIMConfig) -> None:
        self.isim_config = isim_config

    @activity.defn
    async def compute_criticalities_nmap(self) -> str:
        """
        This method computes betweenness and degree centralities based on results
        from Nmap topology scan.
        :return: texts from obtained responses from the REST API endpoints
        """
        async with httpx.AsyncClient() as client:
            first_response = await client.post(f"{self.isim_config.url}/nodes/betweenness_centrality")
            second_response = await client.post(f"{self.isim_config.url}/nodes/degree_centrality")
        return f"First response: {first_response.text}. Second response: {second_response.text}"

    @activity.defn
    async def compute_final_criticalities_nmap(self) -> str:
        """
        This method calls ISIM's REST API endpoint that combines mission criticality
        and betweenness and degree centralities computed on results from Nmap topology scan.
        :return: text from obtained response from the REST API
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.isim_config.url}/nodes/combine_criticality")
        return f"Response: {response.text}"

    def get_activities(self) -> Sequence[Callable[..., Awaitable[Any]]]:
        return [self.compute_criticalities_nmap, self.compute_final_criticalities_nmap]
