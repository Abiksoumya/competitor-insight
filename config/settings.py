# config/settings.py

from pydantic_settings import BaseSettings
# BaseSettings is a special Pydantic class that automatically
# reads values from your .env file. You define the field names
# and it finds the matching environment variable automatically.

class Settings(BaseSettings):

    @property
    def AGENT_LLM_MODEL(self) -> str:
        if self.ANALYST_PROVIDER == "gemini":
            return "gemini/gemini-2.0-flash"
        elif self.ANALYST_PROVIDER == "groq":
            return "groq/llama-3.3-70b-versatile"  # ← best free Groq model
        else:
            return self.CLAUDE_MODEL

    @property
    def AGENT_LLM_API_KEY(self) -> str:
        if self.ANALYST_PROVIDER == "gemini":
            return self.GEMINI_API_KEY
        elif self.ANALYST_PROVIDER == "groq":
            return self.GROQ_API_KEY
        else:
            return self.ANTHROPIC_API_KEY

    # API Keys — Pydantic reads these from .env automatically
    # The field name must match the .env variable name exactly
    ANTHROPIC_API_KEY: str
    SERPER_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # ── NEW ───────────────────────────────────────────
    GEMINI_API_KEY:    str = ""   # optional — only needed for testing
    GROQ_API_KEY:      str = ""   # optional — only needed for testing

    # App config — these have defaults so .env is optional for them
    APP_NAME: str = "Competitor Intelligence Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    ANALYST_PROVIDER:  str = ""

    # Pipeline config
    # How long to wait for scraping before giving up (seconds)
    SCRAPE_TIMEOUT: int = 30
    # Which Claude model to use for the analyst agent
    CLAUDE_MODEL: str = "claude-opus-4-5"
    # Max tokens Claude can use in its response
    CLAUDE_MAX_TOKENS: int = 4000
    MAX_REVIEWS:    int = 50
    CLAUDE_MODEL: str = "anthropic/claude-opus-4-5"
    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY:                str
    JWT_ALGORITHM:                 str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:   int = 30
    REFRESH_TOKEN_EXPIRE_DAYS:     int = 7

    # Admin seed user
    ADMIN_EMAIL:    str = "admin@competitor-intel.com"
    ADMIN_PASSWORD: str = "ChangeMe123!"


    class Config:
        # Tells Pydantic where to find the .env file
        env_file = ".env"
        # If same variable in both .env and system env,
        # system env wins (important for production/Docker)
        env_file_encoding = "utf-8"


# Create ONE instance of Settings — the whole app imports this
# singleton, so .env is only read once at startup, not on every request
settings = Settings()