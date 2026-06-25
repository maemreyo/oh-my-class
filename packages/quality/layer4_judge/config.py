from pydantic_settings import BaseSettings, SettingsConfigDict


class QualityModelConfig(BaseSettings):
	model_config = SettingsConfigDict(
		env_prefix="MODEL_",
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
	)

	llm_judge: str = "f.pro"


QUALITY_MODELS = QualityModelConfig()
