CALL gds.beta.pipeline.linkPrediction.configureSplit($pipeline_name, {
  testFraction: $test_fraction,
  trainFraction: $train_fraction,
  validationFolds: $validation_folds
})
YIELD splitConfig
RETURN splitConfig
