"""This module contains the functionality used for computation of criticality
in the CSA component"""

import json
from typing import List, Any, Dict


def determine_type_of_entity(mission_representation, entity_id) -> str:
    """
    This function determines the type of the entity from the mission representation.
    :param mission_representation: the representation of the mission
    :param entity_id: ID of the entity
    :return: type of the entity, empty string if no type was found
    """
    if hosts_contain_id(mission_representation["nodes"]["hosts"], entity_id):
        return "host"
    if services_contain_id(mission_representation["nodes"]["services"], entity_id):
        return "service"
    if entity_id in mission_representation["nodes"]["aggregations"]["and"]:
        return "AND"
    if entity_id in mission_representation["nodes"]["aggregations"]["or"]:
        return "OR"
    return ""


def determine_numerical_criticality_of_mission(mission: Dict[str, Any]) -> float:
    """
    This function determines the numerical criticality of the mission, which is attached
    as one of properties or computed as maximum of security requirements.
    :param mission: dictionary representation of the mission
    :return: value of mission criticality
    """
    if "criticality" in mission:
        criticality = mission["criticality"]
    elif ("confidentiality_requirement" in mission and "integrity_requirement" in mission and
          "availability_requirement" in mission):
        criticality = max(mission["confidentiality_requirement"],
                          mission["integrity_requirement"],
                          mission["availability_requirement"])
    else:
        raise ValueError(f"Mission {mission} has no criticality nor security requirements.")
    return criticality


def determine_mission_id(mission: Dict[str, Any], structure: Dict[str, Any]) -> str:
    """
    This function determines the id of the mission from the mission representation.
    :param mission: dictionary with properties describing the mission
    :param structure: the relevant part of mission representation
    :return: mission id
    """
    mission_name = mission["name"]
    mission_id = None
    for potential_mission in structure["nodes"]["missions"]:
        if potential_mission["name"] == mission_name:
            mission_id = potential_mission["id"]
    return mission_id


def determine_host_criticalities(hosts_intermediate_results: List[Dict[str, Any]],
                                 structure: Dict[str, Any], final_host_values: List[Dict[str, Any]]) -> None:
    """
    This procedure determines the criticality of the host entities
    based on intermediate results and mission representation.
    :param hosts_intermediate_results: intermediate results of the host entities
    :param structure: relevant part of mission representation
    :param final_host_values: final criticality values of the host entities
    :return:
    """
    for tmp_host_representation in hosts_intermediate_results:
        for potential_host in structure["nodes"]["hosts"]:
            if potential_host["id"] == tmp_host_representation["id"]:
                final_representation = {"criticality": tmp_host_representation["criticality"],
                                        "hostname": potential_host["hostname"],
                                        "ip": potential_host["ip"]}
                host_index = index_in_host_list(final_representation, final_host_values)
                if host_index != -1:
                    if final_representation["criticality"] > final_host_values[host_index][
                        "criticality"]:
                        final_host_values[host_index]["criticality"] = final_representation[
                            "criticality"]
                else:
                    final_host_values.append(final_representation)


def index_in_host_list(host_dict, host_list):
    """
    This function returns the index of the host described by host_dict in host_list.
    :param host_dict: dictionary of the host's properties
    :param host_list: list of hosts
    :return: index of the host
    """
    index = 0
    for host in host_list:
        if host["hostname"] == host_dict["hostname"] and host["ip"] == host_dict["ip"]:
            return index
        index += 1
    return -1


def hosts_contain_id(hosts_data, host_id):
    """
    This function determines whether a host with host ID is contained within hosts data.
    :param hosts_data: list of hosts
    :param host_id: id of a host
    :return: True if host is contained within hosts data, False otherwise
    """
    for host in hosts_data:
        if host_id == host['id']:
            return True
    return False


def services_contain_id(services_data, service_id):
    """
    This function determines whether a service with service ID is contained within services data.
    :param services_data: list of services
    :param service_id: id of service
    :return: True if service_id corresponds to a service from the list, False otherwise
    """
    for service in services_data:
        if service_id == service['id']:
            return True
    return False


def compute_criticalities_of_hosts(missions: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    This procedure computes the criticality of hosts based on the mission representations.
    :param missions: list of mission representations
    :return: list of criticalities for hosts
    """
    final_hosts = []
    for mission_representation in missions:
        mission = mission_representation[0]
        criticality = determine_numerical_criticality_of_mission(mission)

        if "structure" in mission:
            structure = json.loads(mission["structure"])
        else:
            raise ValueError(f"Mission {mission} does not contain JSON representing its structure.")

        unprocessed_entities = [{"id": determine_mission_id(mission, structure),
                                 "criticality": criticality, "type": "mission"}]
        hosts_intermediate_results = []

        while unprocessed_entities:
            unprocessed_entity = unprocessed_entities.pop(0)
            count_of_children = 0
            if unprocessed_entity["type"] == "OR":
                for relationship in structure["relationships"]["one_way"]:
                    if relationship["from"] == unprocessed_entity["id"]:
                        count_of_children += 1
            if unprocessed_entity["type"] == "host":
                hosts_intermediate_results.append(unprocessed_entity)
                continue
            for relationship in structure["relationships"]["one_way"]:
                if relationship["from"] == unprocessed_entity["id"]:
                    unprocessed_entities.append(
                        {"id": relationship["to"],
                         "criticality": unprocessed_entity["criticality"] if unprocessed_entity["type"] != "OR" else unprocessed_entity["criticality"]/count_of_children,
                         "type": determine_type_of_entity(structure, relationship["to"])})

        determine_host_criticalities(hosts_intermediate_results, structure, final_hosts)

    return final_hosts
