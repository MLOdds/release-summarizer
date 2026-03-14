from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    model: str = "gpt-5-mini"  # .env'de MODEL=... şeklinde override edilebilir
    # LiteLLM ile non-OpenAI model kullanımı için (örn: anthropic/claude-3-5-sonnet-20240620)
    # MODEL değeri provider/model formatında olmalı, LITELLM_API_KEY sağlayıcıya ait key
    litellm_api_key: str = ""
    # Self-hosted LiteLLM proxy için base URL (örn: http://localhost:4000)
    # Boş bırakılırsa LiteLLM doğrudan sağlayıcı API'sine bağlanır
    litellm_base_url: str = ""
    github_token: str = ""
    max_concurrent_ai: int = 4   # Paralel AI çağrısı limiti — RPM/TPM rate limit koruması
    source_timeout: int = 90     # Tek kaynak için toplam timeout (fetch + summarize)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
