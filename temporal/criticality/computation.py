import json
from typing import List, Any, Dict


def determine_type_of_entity(mission_representation, entity_id):
    if hosts_contain_id(mission_representation["nodes"]["hosts"], entity_id):
        return "host"
    elif services_contain_id(mission_representation["nodes"]["services"], entity_id):
        return "service"
    elif entity_id in mission_representation["nodes"]["aggregations"]["and"]:
        return "AND"
    elif entity_id in mission_representation["nodes"]["aggregations"]["or"]:
        return "OR"


def compute_criticalities_of_hosts(missions: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    final_hosts = []
    for mission_representation in missions:
        mission = mission_representation[0]

        if "criticality" in mission:
            criticality = mission["criticality"]
        elif "confidentiality_requirement" in mission and "integrity_requirement" in mission and "availability_requirement" in mission:
            criticality = max(mission["confidentiality_requirement"], mission["integrity_requirement"],
                              mission["availability_requirement"])
        else:
            raise ValueError(f"Mission {mission} has no criticality nor security requirements.")

        if "structure" in mission:
            structure = json.loads(mission["structure"])
        else:
            raise ValueError(f"Mission {mission} does not contain JSON representing its structure.")

        mission_name = mission["name"]
        mission_id = None
        for potential_mission in structure["nodes"]["missions"]:
            if potential_mission["name"] == mission_name:
                mission_id = potential_mission["id"]
        unprocessed_entities = [{"id": mission_id, "criticality": criticality, "type": "mission"}]
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
                    unprocessed_entities.append({"id": relationship["to"],
                                                 "criticality": unprocessed_entity["criticality"] if unprocessed_entity["type"] != "OR" else unprocessed_entity["criticality"]/count_of_children,
                                                 "type": determine_type_of_entity(structure, relationship["to"])})

        for tmp_host_representation in hosts_intermediate_results:
            for potential_host in structure["nodes"]["hosts"]:
                if potential_host["id"] == tmp_host_representation["id"]:
                    final_representation = {"criticality": tmp_host_representation["criticality"],
                                            "hostname": potential_host["hostname"],
                                            "ip": potential_host["ip"]}
                    host_index = index_in_host_list(final_representation, final_hosts)
                    if host_index != -1:
                        if final_representation["criticality"] > final_hosts[host_index][
                            "criticality"]:
                            final_hosts[host_index]["criticality"] = final_representation[
                                "criticality"]
                    else:
                        final_hosts.append(final_representation)

    return final_hosts

def index_in_host_list(host_dict, host_list):
    index = 0
    for host in host_list:
        if host["hostname"] == host_dict["hostname"] and host["ip"] == host_dict["ip"]:
            return index
        index += 1
    return -1


def hosts_contain_id(hosts_data, host_id):
    """
    True if host_id is id of a host.

    :param hosts_data: list of hosts
    :param host_id: id of a host
    :return: True or False
    """
    for host in hosts_data:
        if host_id == host['id']:
            return True
    return False


def services_contain_id(services_data, service_id):
    """
    Tests if service_id is id of service.

    :param services_data: list of services
    :param service_id: id of service
    :return: True if service_id is service
    """
    for service in services_data:
        if service_id == service['id']:
            return True
    return False
