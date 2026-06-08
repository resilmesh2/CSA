CALL gds.beta.pipeline.linkPrediction.create($pipeline_name)
YIELD name, nodePropertySteps, featureSteps, splitConfig, autoTuningConfig
RETURN name, nodePropertySteps, featureSteps, splitConfig, autoTuningConfig
