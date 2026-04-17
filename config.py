from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM provider
    LLM_PROVIDER: Literal["claude", "ollama"] = os.getenv("LLM_PROVIDER", "claude")

    # Claude
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
    CLAUDE_FORMATTING_MODEL: str = os.getenv(
        "CLAUDE_FORMATTING_MODEL", "claude-haiku-4-5-20251001"
    )

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b")
    OLLAMA_FORMATTING_MODEL: str = os.getenv("OLLAMA_FORMATTING_MODEL", "llama3.1:8b")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///db/sample.db")
    # Raw ODBC connection string for SQL Server
    # e.g. DRIVER={SQL Server};SERVER=host,port;DATABASE=db;UID=user;PWD=pass
    MSSQL_CONNECTION_STRING: str = os.getenv("MSSQL_CONNECTION_STRING", "")

    # Agent behaviour
    MAX_ROWS_RETURNED: int = int(os.getenv("MAX_ROWS_RETURNED", "100"))
    MAX_ERROR_RECOVERY_ATTEMPTS: int = int(
        os.getenv("MAX_ERROR_RECOVERY_ATTEMPTS", "3")
    )
    ALLOW_WRITE_QUERIES: bool = os.getenv("ALLOW_WRITE_QUERIES", "false").lower() == "true"
    ENABLE_PROMPT_CACHING: bool = os.getenv("ENABLE_PROMPT_CACHING", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def formatting_model(cls) -> str:
        if cls.LLM_PROVIDER == "ollama":
            return cls.OLLAMA_FORMATTING_MODEL
        return cls.CLAUDE_FORMATTING_MODEL
