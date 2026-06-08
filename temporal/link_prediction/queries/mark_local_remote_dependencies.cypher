MATCH (n1)-[r1:DIRECT_DEPENDENCY]->(n2)-[r2:DIRECT_DEPENDENCY]->(n3)
WHERE EXISTS {
  MATCH (n1)-[r3:IS_CONNECTED_TO]->(n2)-[r4:IS_CONNECTED_TO]->(n3)
  WHERE r3.start <= r4.start <= r4.end <= r3.end
  RETURN n1, n2, n3
}
SET r1.found = TRUE, r2.found = TRUE
RETURN count(*) AS dependenciesMarked
