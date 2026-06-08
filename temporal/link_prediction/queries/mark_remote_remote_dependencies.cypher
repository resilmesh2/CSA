MATCH (n1)-[r1:DIRECT_DEPENDENCY]->(n2)-[r2:DIRECT_DEPENDENCY]->(n3)
WHERE EXISTS {
  MATCH (n2)<-[r3:IS_CONNECTED_TO]-(n1)-[r4:IS_CONNECTED_TO]->(n3)
  WHERE r3.end <= r4.start AND r4.start - r3.end <= $epsilon
}
SET r1.found = TRUE, r2.found = TRUE
RETURN count(*) AS dependenciesMarked
