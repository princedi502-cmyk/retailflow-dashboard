from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):

    MONGO_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME:str = "retail_flow"
    SECRET_KEY: str
    DEBUG: bool = False
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()