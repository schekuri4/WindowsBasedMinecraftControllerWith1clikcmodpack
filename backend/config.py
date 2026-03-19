"""
MCServerPanel - Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "MCServerPanel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    SERVERS_DIR: Path = DATA_DIR / "servers"
    BACKUPS_DIR: Path = DATA_DIR / "backups"
    TEMP_DIR: Path = DATA_DIR / "temp"
    DB_PATH: Path = DATA_DIR / "mcserverpanel.db"

    # Server defaults
    DEFAULT_MIN_RAM: str = "1G"
    DEFAULT_MAX_RAM: str = "4G"
    DEFAULT_JVM_ARGS: str = "-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200"
    DEFAULT_PORT: int = 25565

    # API settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # External APIs
    CURSEFORGE_API_KEY: str = ""
    MODRINTH_API_URL: str = "https://api.modrinth.com/v2"
    CURSEFORGE_API_URL: str = "https://api.curseforge.com/v1"
    MINECRAFT_GAME_ID: int = 432  # CurseForge game ID for Minecraft

    # Java detection paths (Windows)
    JAVA_SEARCH_PATHS: list[str] = [
        r"C:\Program Files\Java",
        r"C:\Program Files (x86)\Java",
        r"C:\Program Files\Eclipse Adoptium",
        r"C:\Program Files\AdoptOpenJDK",
        r"C:\Program Files\Zulu",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
for d in [settings.DATA_DIR, settings.SERVERS_DIR, settings.BACKUPS_DIR, settings.TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)
