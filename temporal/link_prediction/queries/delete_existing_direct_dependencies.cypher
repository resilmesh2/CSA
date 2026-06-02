MATCH ()-[r:DIRECT_DEPENDENCY]->()
DELETE r
RETURN count(r) AS dependenciesDeleted
