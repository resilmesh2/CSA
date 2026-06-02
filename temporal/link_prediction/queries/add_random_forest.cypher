CALL gds.beta.pipeline.linkPrediction.addRandomForest($pipeline_name, {
  numberOfDecisionTrees: $number_of_decision_trees,
  maxDepth: $max_depth
})
YIELD parameterSpace
RETURN parameterSpace
