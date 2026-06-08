CALL gds.beta.pipeline.linkPrediction.addNodeProperty($pipeline_name, 'Node2Vec', {
  mutateProperty: 'embedding',
  embeddingDimension: $embedding_dimension,
  walkLength: $walk_length,
  walksPerNode: $walks_per_node,
  windowSize: $window_size,
  negativeSamplingRate: $negative_sampling_rate,
  iterations: $iterations
})
YIELD nodePropertySteps
RETURN nodePropertySteps
