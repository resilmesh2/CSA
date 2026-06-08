CALL gds.alpha.pipeline.linkPrediction.configureAutoTuning($pipeline_name, {
  maxTrials: $max_trials
})
YIELD autoTuningConfig
RETURN autoTuningConfig
