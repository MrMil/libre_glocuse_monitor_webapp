from pydantic_settings import BaseSettings, SettingsConfigDict
from pylibrelinkup import APIUrl


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    libre_email: str
    libre_password: str
    libre_region: str = "US"

    @property
    def api_url(self) -> APIUrl:
        return APIUrl.from_string(self.libre_region)


settings = Settings()
