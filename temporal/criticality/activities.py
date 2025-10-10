"""This module contains activities used during the computation of criticality
in the CSA component."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, List
import httpx

from config import ISIMConfig
from temporalio import activity
from temporal.criticality.computation import compute_criticalities_of_hosts


class CriticalityActivities:
    """A class for activities used during the computation of criticality."""
    def __init__(self, isim_config: ISIMConfig) -> None:
        self.isim_config = isim_config

    @activity.defn
    async def compute_mission_criticalities(self) -> List[dict[str, Any]]:
        """
        This method obtains missions from the database, executes computation of criticalities
        for hosts that appeared in representations of missions obtained from the database,
        and returns the results as a list.
        :return: computed mission criticalities for hosts
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.isim_config.url}/missions")
            output_data = compute_criticalities_of_hosts(response.json())
        return output_data

    @activity.defn
    async def store_mission_criticalities(self, missions_hosts_criticalities: List[dict[str, Any]]
                                          ) -> str:
        """
        This method stores computed criticalities of hosts from mission representations by
        calling an appropriate REST API endpoint of ISIM.
        :param missions_hosts_criticalities: computes criticalities of hosts from mission
        representations
        :return: text from the obtained response from the REST API endpoint
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.isim_config.url}/nodes/store_criticality",
                                         json=missions_hosts_criticalities)
            return response.text

    @activity.defn
    async def compute_final_criticalities(self) -> str:
        """
        This method calls ISIM's REST API endpoint that combines mission criticality
        and betweenness and degree centralities.
        :return: text from obtained response from the REST API
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.isim_config.url}/nodes/combine_criticality")
        return response.text

    def get_activities(self) -> Sequence[Callable[..., Awaitable[Any]]]:
        return [self.compute_mission_criticalities, self.store_mission_criticalities,
                self.compute_final_criticalities]
