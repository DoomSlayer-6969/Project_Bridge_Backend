from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """All values come from the environment / .env; missing ones fail at startup."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str
    api_v1_prefix: str

    db_driver: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    cookie_secure: bool

    @property
    def database_url(self) -> str:
        # URL.create escapes special characters in the credentials.
        return URL.create(
            drivername=self.db_driver,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


settings = Settings()
