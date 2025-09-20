import os

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_port: int = Field(default=8000, alias="API_PORT")

    postgres_db: str = Field(default="idp", alias="POSTGRES_DB")
    postgres_user: str = Field(default="idp", alias="POSTGRES_USER")
    postgres_password: str = Field(default="changeme", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    jwt_secret: str = Field(default="change-this-in-prod", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # S3 / MinIO
    s3_endpoint_url: str = Field(default="http://minio:9000", alias="S3_ENDPOINT_URL")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="idp", alias="S3_BUCKET")
    s3_use_ssl: bool = Field(default=False, alias="S3_USE_SSL")

    download_url_expire_seconds: int = Field(
        default=3600, alias="DOWNLOAD_URL_EXPIRE_SECONDS"
    )
    max_upload_mb: int = Field(default=50, alias="MAX_UPLOAD_MB")

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def sql_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()  # Load at import time
