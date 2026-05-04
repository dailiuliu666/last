import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


class Settings:
    app_name = os.getenv("APP_NAME", "Graduation Finance Platform")
    app_env = os.getenv("APP_ENV", "dev")
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "8001"))

    mysql_host = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_db = os.getenv("MYSQL_DB", "graduation_finance")
    mysql_charset = os.getenv("MYSQL_CHARSET", "utf8mb4")

    tushare_token = os.getenv("TUSHARE_TOKEN", "")
    predictor_model_dir = os.getenv("PREDICTOR_MODEL_DIR", "model_artifacts")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset={self.mysql_charset}"
        )


settings = Settings()
