import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    nvidia_nim_key: str = os.getenv("NVIDIA_NIM_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentos.db")
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500",
        ).split(",")
        if o.strip()
    ]
    debug: bool = True
    agent_timeout: int = 90
    max_agents: int = 12


settings = Settings()
