from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "Skyreon Workforce Portal"
    database_url: str = "postgresql+asyncpg://skyreon:skyreon@localhost:5433/skyreon"
    supabase_database_url: str = ""
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:3000"
    admin_email: str = "admin@skyreon.com"
    admin_password: str = "ChangeMe123!"
    admin_name: str = "Skyreon Admin"
    super_admin_email: str = "superadmin@skyreon.com"
    super_admin_password: str = "ChangeMe123!"

    @property
    def resolved_database_url(self) -> str:
        return (self.supabase_database_url or self.database_url).strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_production_security(self) -> None:
        if self.cookie_secure and (
            self.jwt_secret == "change-me-to-a-long-random-string" or len(self.jwt_secret) < 32
        ):
            raise RuntimeError(
                "Insecure JWT_SECRET: set a random secret of at least 32 characters in production."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
