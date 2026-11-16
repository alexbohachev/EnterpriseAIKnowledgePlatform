"""Explicit runtime configuration; secrets are never checked into source control."""
from pathlib import Path
from urllib.parse import urlsplit
from pydantic import model_validator
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EAKP_", extra="ignore")

    database_url: str = "sqlite:///./eakp-local.db"  # only local Python development
    storage_root: Path = Path("./storage")
    jwt_secret: str = Field(min_length=32)  # required; no insecure default
    jwt_issuer: str = "eakp-local"
    jwt_audience: str = "eakp-api"
    jwt_minutes: int = Field(default=30, ge=5, le=120)
    # All endpoints point to Docker-internal/localhost services, not hosted providers.
    ollama_url: str = "http://localhost:11434"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "eakp_chunks_v1"
    embedding_model: str = "bge-m3"
    embedding_dim: int = Field(default=1024, ge=1, le=8192)
    chat_model: str = "qwen2.5:3b"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # required when Stage 4 runtime is enabled
    max_upload_mb: int = Field(default=12, ge=1, le=100)
    max_pdf_pages: int = Field(default=100, ge=1, le=1000)
    login_max_per_minute: int = Field(default=8, ge=2, le=1000)
    query_max_per_minute: int = Field(default=30, ge=1, le=5000)
    upload_max_per_minute: int = Field(default=12, ge=1, le=5000)
    # Telemetry is opt-in. Never configure a public collector. /internal/metrics is
    # disabled unless an independent monitoring bearer token is supplied.
    metrics_token: str = ""
    otlp_traces_endpoint: str = ""
    # Network allowlist is a configuration guardrail, not a host firewall.
    trusted_service_hosts: str = "localhost,127.0.0.1,ollama,qdrant,neo4j,otel-collector"
    allowed_http_hosts: str = "localhost,127.0.0.1,api,testserver"
    max_extracted_chars: int = Field(default=1_000_000, ge=1000)
    # OCR is opt-in for local Python runs, enabled explicitly in Docker Compose.
    ocr_enabled: bool = False
    ocr_languages: str = "eng+ukr+rus"
    ocr_dpi: int = Field(default=170, ge=100, le=250)
    ocr_timeout_seconds: int = Field(default=25, ge=5, le=90)
    ocr_max_pages: int = Field(default=20, ge=1, le=100)

    @field_validator("ocr_languages")
    @classmethod
    def validate_ocr_languages(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"[a-z]{3}(?:\+[a-z]{3}){0,3}", value):
            raise ValueError("OCR languages must be 3-letter codes separated by +")
        return value


    @field_validator("jwt_secret")
    @classmethod
    def no_placeholder(cls, value: str) -> str:
        low = value.lower()
        if any(token in low for token in ("changeme", "replace", "placeholder", "example-secret")) or len(set(value)) < 8:
            raise ValueError("JWT secret must be unique and non-placeholder")
        return value

    @field_validator("metrics_token")
    @classmethod
    def validate_metrics_token(cls, value: str) -> str:
        if value and (len(value) < 24 or len(set(value)) < 8 or "replace" in value.lower()):
            raise ValueError("Telemetry secret must be random and at least 24 characters")
        return value

    @model_validator(mode="after")
    def validate_local_service_endpoints(self):
        hosts = {h.strip().lower() for h in self.trusted_service_hosts.split(",") if h.strip()}
        for label, endpoint, schemes in (
            ("ollama_url", self.ollama_url, {"http", "https"}),
            ("qdrant_url", self.qdrant_url, {"http", "https"}),
            ("neo4j_uri", self.neo4j_uri, {"bolt", "bolt+s", "bolt+ssc"}),
        ):
            parsed = urlsplit(endpoint)
            if parsed.scheme not in schemes or not parsed.hostname or parsed.hostname.lower() not in hosts:
                raise ValueError(f"{label}: host/scheme not allowlisted for offline deployment")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError(f"{label}: credentials, query and fragment forbidden in URL")
        if self.otlp_traces_endpoint:
            endpoint = urlsplit(self.otlp_traces_endpoint)
            if (endpoint.scheme != "http" or endpoint.hostname not in hosts or
                endpoint.path != "/v1/traces" or endpoint.username or endpoint.password or
                endpoint.query or endpoint.fragment):
                raise ValueError("OTLP collector must be a local allowlisted http:// host /v1/traces")
        return self
