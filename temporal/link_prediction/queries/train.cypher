CALL gds.beta.pipeline.linkPrediction.train($graph_name, {
  pipeline: $pipeline_name,
  modelName: $model_name,
  metrics: ['AUCPR', 'OUT_OF_BAG_ERROR'],
  targetRelationshipType: 'POTENTIAL_DEPENDENCY'
}) YIELD modelInfo, modelSelectionStats
RETURN
  modelInfo.bestParameters AS winningModel,
  modelInfo.metrics.AUCPR.train.avg AS avgTrainScore,
  modelInfo.metrics.AUCPR.outerTrain AS outerTrainScore,
  modelInfo.metrics.AUCPR.test AS testScore,
  [cand IN modelSelectionStats.modelCandidates | cand.metrics.AUCPR.validation.avg] AS validationScores
