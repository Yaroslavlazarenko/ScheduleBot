from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Строго типізована конфігурація додатку."""
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    telegram_bot_token: str
    api_base_url: str
    api_key: str

settings = Settings() # type: ignore