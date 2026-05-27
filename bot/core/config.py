from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    bot_token: SecretStr
    openai_api_key: SecretStr
    database_url: str
    redis_url: str
    daily_cost_limit_usd: float = 3.0
    webhook_url: str | None = None

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

config = Settings()
