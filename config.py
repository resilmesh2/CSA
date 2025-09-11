from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dacite import from_dict

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
class Config:
    temporal: TemporalConfig
    isim: ISIMConfig

class AppConfig:
    _config: Config | None = None

    @classmethod
    def get(cls) -> Config:
        if cls._config is None:
            config_file = BASE_DIR / "config/config.yaml"
            with Path.open(config_file, "r") as f:
                raw_config = yaml.safe_load(f)
            cls._config = from_dict(Config, raw_config)
        return cls._config
