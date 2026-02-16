from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stripe_api_key: str
    stripe_webhook_secret: str
    db_path: str = "/data/billing/billing.db"
    host: str = "0.0.0.0"
    port: int = 8004


settings = Settings()
