CALL gds.beta.pipeline.linkPrediction.addFeature($pipeline_name, 'hadamard', {
  nodeProperties: ['embedding']
}) YIELD featureSteps
RETURN featureSteps
