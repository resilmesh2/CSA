CALL gds.graph.relationshipProperty.stream(
  $graph_name,
  'probability',
  ['PREDICTED_DEPENDENCY']
)
YIELD sourceNodeId, targetNodeId, relationshipType, propertyValue
WITH
  gds.util.asNode(sourceNodeId) AS sourceNode,
  gds.util.asNode(targetNodeId) AS targetNode,
  relationshipType,
  propertyValue AS probability
OPTIONAL MATCH (sourceNode)-[:IS_A]-(sourceHost:Host)
OPTIONAL MATCH (sourceNode)-[:HAS_ASSIGNED]-(sourceIp:IP)
WITH
  sourceNode,
  targetNode,
  relationshipType,
  probability,
  collect(DISTINCT sourceHost.hostname) AS sourceHostnames,
  collect(DISTINCT sourceIp.address) AS sourceIpAddresses
OPTIONAL MATCH (targetNode)-[:IS_A]-(targetHost:Host)
OPTIONAL MATCH (targetNode)-[:HAS_ASSIGNED]-(targetIp:IP)
WITH
  sourceNode,
  targetNode,
  relationshipType,
  probability,
  sourceHostnames,
  sourceIpAddresses,
  collect(DISTINCT targetHost.hostname) AS targetHostnames,
  collect(DISTINCT targetIp.address) AS targetIpAddresses
RETURN
  elementId(sourceNode) AS sourceElementId,
  coalesce(sourceHostnames[0], sourceIpAddresses[0], elementId(sourceNode)) AS sourceName,
  sourceHostnames,
  sourceIpAddresses,
  labels(sourceNode) AS sourceLabels,
  properties(sourceNode) AS sourceProperties,
  elementId(targetNode) AS targetElementId,
  coalesce(targetHostnames[0], targetIpAddresses[0], elementId(targetNode)) AS targetName,
  targetHostnames,
  targetIpAddresses,
  labels(targetNode) AS targetLabels,
  properties(targetNode) AS targetProperties,
  relationshipType,
  probability
ORDER BY probability DESC
LIMIT $prediction_limit
