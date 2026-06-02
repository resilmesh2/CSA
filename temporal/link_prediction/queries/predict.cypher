CALL gds.beta.pipeline.linkPrediction.predict.mutate($graph_name, {
  modelName: $model_name,
  relationshipTypes: ['POTENTIAL_DEPENDENCY'],
  mutateRelationshipType: 'PREDICTED_DEPENDENCY',
  mutateProperty: 'probability',
  topN: $top_n,
  threshold: $threshold
}) YIELD relationshipsWritten, samplingStats
RETURN relationshipsWritten, samplingStats
