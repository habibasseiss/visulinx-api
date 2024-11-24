from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8'
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    AWS_ACCESS_KEY_ID: str
    AWS_ENDPOINT_URL_S3: str
    AWS_REGION: str
    AWS_SECRET_ACCESS_KEY: str
    BUCKET_NAME: str

    def get_database_url(self) -> str:
        url = self.DATABASE_URL
        if 'postgres://' in url:
            url = url.replace('postgres://', 'postgresql://')
        return url
