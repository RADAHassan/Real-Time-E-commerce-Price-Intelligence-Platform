from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "local")
    bigquery_dataset: str = os.getenv("BIGQUERY_DATASET", "price_intelligence")
    bigquery_location: str = os.getenv("BIGQUERY_LOCATION", "US")
    # Set USE_MOCK_DATA=true for local dev without GCP credentials
    use_mock_data: bool = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
    api_title: str = "Price Intelligence API"
    api_version: str = "1.0.0"
    cors_origins: list[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # alternative dev port
        "http://localhost:8501",   # Streamlit
        "http://frontend",         # Docker network
    ]

    @property
    def marts_dataset(self) -> str:
        return f"{self.bigquery_dataset}_marts"

    @property
    def raw_dataset(self) -> str:
        return f"{self.bigquery_dataset}_raw"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
