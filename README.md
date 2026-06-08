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
the database contains enterprise missions and results from Nmap topology scan provided by CASM or IP flow data. 
Therefore, consider running also the other components when running CSA.

The workflow orchestrator repository contains several docker containers that provide Temporal’s functionality. 
The CSA worker communicates with the Temporal container, which must be up before the deployment. The CSA repository contains two workflows that compute criticalities of network nodes. One of them uses IP flow data and the second one uses results from Nmap topology scan.

A workflow for computing criticalities of network nodes using IP flow data can be executed using

```shell
docker exec -it <csa-worker-id> python -m temporal.criticality.ip_flow.workflow
```

A workflow for computing criticalities of network nodes using results from Nmap topology scan can be executed using

```shell
docker exec -it <csa-worker-id> python -m temporal.criticality.nmap_topology.workflow
```

A workflow for running the link prediction experiment can be executed using

```shell
docker exec -it <csa-worker-id> python -m temporal.link_prediction.workflow
```

Default link prediction parameters are stored in `config/config.yaml` under the `link_prediction` section. Any workflow input fields override those configured defaults:

```shell
docker exec -it <csa-worker-id> python -m temporal.link_prediction.workflow '{"top_n": 50, "threshold": 0.5, "prediction_limit": 20}'
```

The workflow can also be started from Temporal UI with workflow type `LinkPredictionWorkflow`, task queue `csa`, and one JSON object argument. Omit the input to use configured defaults, or pass only fields to override:

```json
{
  "top_n": 50,
  "threshold": 0.5,
  "prediction_limit": 20
}
```

Results for IP flow data in the Neo4j database can be checked by running:

```
MATCH (n:Node) RETURN n.degree_centrality_norm, n.pagerank_centrality_norm, 
n.mission_criticality, n.final_criticality_flows
```

Results for data from Nmap topology scan in the Neo4j database can be checked by running:

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
