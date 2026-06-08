MATCH (n1:Node)-[r1:IS_CONNECTED_TO]-(n2:Node)
WITH n1, n2, count(r1) AS r1_count
WHERE r1_count >= $r1_count_min
MERGE (n1)-[:DIRECT_DEPENDENCY]->(n2)
RETURN count(*) AS dependenciesProcessed
