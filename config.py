from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Строго типізована конфігурація додатку."""
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    telegram_bot_token: str
    # Всі змінні, пов'язані з API, успішно видалені!

settings = Settings() # type: ignore