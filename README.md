# CSA - Critical Service Awareness

This component implements computation of criticality for network nodes. It has a dependency on 
[ISIM](https://github.com/resilmesh2/ISIM) and
[workflow orchestrator](https://github.com/resilmesh2/Workflow-Orchestrator) that must be running 
before deploying the CSA worker.

## How to Run
The CSA worker container can be deployed by running

```shell
docker compose up -d
```

It is necessary to execute docker compose for ISIM too. This component relies on its database and 
REST API. Moreover, this component will produce meaningful or any results at all only when 
the database contains enterprise missions and results from Nmap topology scan provided by CASM. 
Therefore, consider running also the other components when running CSA.

The workflow orchestrator repository contains several docker containers that provide Temporal’s functionality. 
The CSA worker communicates with the Temporal container, which must be up before the deployment.

A workflow for computing criticalities of network nodes can be executed with

```shell
docker exec -it <csa-worker-id> python -m temporal.criticality.workflow
```

Results in the Neo4j database can be checked by running:

```
MATCH (n:Node) RETURN n.mission_criticality, n.topology_degree_norm, 
n.topology_betweenness_norm, n.final_criticality
```

# Versions Used During Testing
CASM was successfully tested with the following OS configuration and docker versions. 
Versions of software packages can be found in `poetry.lock` and `pyproject.toml` files.
These versions of software packages are automatically deployed when docker is used according to 
instructions from this README.md file.

|Operating System|Docker Version|Docker Compose Version| Memory |CPU Architecture|Number of Cores|
|----------------|--------------|----------------------|--------|----------------|---------------|
|Ubuntu 24.04.2 LTS|28.3.3|v2.39.1|64.0 GiB|x86_64|16|