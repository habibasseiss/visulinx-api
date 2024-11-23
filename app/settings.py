from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    def get_database_url(self) -> str:
        url = self.DATABASE_URL
        if 'postgres://' in url:
            url = url.replace('postgres://', 'postgresql://')
        return url
