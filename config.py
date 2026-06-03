from dataclasses import dataclass
from pathlib import Path

import yaml
from dacite import from_dict
from temporal.link_prediction.shared import LinkPredictionParams

BASE_DIR = Path(__file__).resolve().parent

TEMPORAL_URL = "temporal:7233"
TEMPORAL_NAMESPACE = "default"

@dataclass
class TemporalConfig:
    url: str = TEMPORAL_URL
    namespace: str = TEMPORAL_NAMESPACE
    csa_task_queue: str = "csa"

@dataclass
class ISIMConfig:
    url: str


@dataclass
class Neo4jConfig:
    password: str = "supertestovaciheslo"
    bolt: str = "bolt://resilmesh-sap-neo4j:7687"
    user: str = "neo4j"


@dataclass
class Config:
    temporal: TemporalConfig
    isim: ISIMConfig
    neo4j: Neo4jConfig
    link_prediction: LinkPredictionParams

class AppConfig:
    _config: Config | None = None

    @classmethod
    def get(cls) -> Config:
        if cls._config is None:
            config_file = BASE_DIR / "config/config.yaml"
            with Path.open(config_file, "r") as f:
                raw_config = yaml.safe_load(f)
            raw_config["link_prediction"] = LinkPredictionParams.model_validate(
                raw_config["link_prediction"]
            )
            cls._config = from_dict(Config, raw_config)
        return cls._config
