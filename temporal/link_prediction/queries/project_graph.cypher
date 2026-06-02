MATCH (n1)-[r:DIRECT_DEPENDENCY {found: TRUE}]->(n2)
WITH gds.graph.project($graph_name, n1, n2, {
    sourceNodeLabels: labels(n1),
    targetNodeLabels: labels(n2),
    relationshipType: 'POTENTIAL_DEPENDENCY'},
    {undirectedRelationshipTypes: ['*']}) AS g
RETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels
