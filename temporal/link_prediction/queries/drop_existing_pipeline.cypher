CALL gds.pipeline.drop($pipeline_name, false)
YIELD pipelineName
RETURN pipelineName
