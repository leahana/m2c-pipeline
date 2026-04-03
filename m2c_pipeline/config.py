"""
Vertex AI configuration management for m2c_pipeline.
All parameters are loaded from environment variables with sensible defaults.
"""

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


def _parse_dotenv_line(line: str) -> Optional[Tuple[str, str]]:
    """Parse a minimal .env line.

    Supports:
    - KEY=value
    - export KEY=value
    - quoted values via shlex
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if stripped.startswith("export "):
        stripped = stripped[len("export "):].strip()

    if "=" not in stripped:
        return None

    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    raw_value = raw_value.strip()
    if not key:
        return None

    try:
        parsed = shlex.split(raw_value, comments=True, posix=True)
    except ValueError:
        parsed = [raw_value]

    if not parsed:
        value = ""
    elif len(parsed) == 1:
        value = parsed[0]
    else:
        value = " ".join(parsed)

    return key, value


def load_local_env() -> None:
    """Load `.env` from cwd first, then repo root, without overriding shell env."""
    candidates = []
    cwd_env = Path.cwd() / ".env"
    repo_env = Path(__file__).resolve().parent.parent / ".env"
    for path in (cwd_env, repo_env):
        if path not in candidates and path.exists():
            candidates.append(path)

    for path in candidates:
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_dotenv_line(line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)


@dataclass
class VertexConfig:
    """Central configuration for all Vertex AI API parameters.

    Load via VertexConfig.from_env() — never hardcode secrets.
    Authentication uses Google Cloud Application Default Credentials (ADC).
    """

    # === Required ===
    project_id: str = ""

    # === Vertex AI ===
    location: str = "us-central1"
    gemini_model: str = "gemini-2.0-flash"
    # Gemini native image generation model (uses google-genai SDK, location=global)
    image_model: str = "gemini-3.1-flash-image-preview"

    # === Image generation params ===
    # Supported values for gemini-3.1-flash-image-preview / gemini-3-pro-image-preview:
    # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
    aspect_ratio: str = "1:1"

    # === Pipeline ===
    output_dir: str = "./output"
    template_name: str = "chiikawa"

    # === Concurrency ===
    # max_workers=2 is conservative: image gen takes 45-200s and is quota-sensitive
    max_workers: int = 2
    # request_timeout covers worst-case image gen (observed 200s for 4.6K-token prompt)
    request_timeout: int = 600  # seconds

    # === Retry (tenacity) ===
    max_retries: int = 5
    retry_min_wait: int = 2   # seconds
    retry_max_wait: int = 60  # seconds

    # === Logging ===
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "VertexConfig":
        """Load configuration from M2C_* environment variables."""
        load_local_env()
        return cls(
            project_id=os.environ.get("M2C_PROJECT_ID", ""),
            location=os.environ.get("M2C_LOCATION", "us-central1"),
            gemini_model=os.environ.get("M2C_GEMINI_MODEL", "gemini-2.0-flash"),
            image_model=os.environ.get("M2C_IMAGE_MODEL", "gemini-3.1-flash-image-preview"),
            aspect_ratio=os.environ.get("M2C_ASPECT_RATIO", "1:1"),
            output_dir=os.environ.get("M2C_OUTPUT_DIR", "./output"),
            template_name=os.environ.get("M2C_TEMPLATE", "chiikawa"),
            max_workers=int(os.environ.get("M2C_MAX_WORKERS", "2")),
            request_timeout=int(os.environ.get("M2C_REQUEST_TIMEOUT", "600")),
            max_retries=int(os.environ.get("M2C_MAX_RETRIES", "5")),
            retry_min_wait=int(os.environ.get("M2C_RETRY_MIN_WAIT", "2")),
            retry_max_wait=int(os.environ.get("M2C_RETRY_MAX_WAIT", "60")),
            log_level=os.environ.get("M2C_LOG_LEVEL", "INFO"),
        )

    def apply_overrides(self, **kwargs) -> "VertexConfig":
        """Return a new VertexConfig with CLI overrides applied (non-None values only)."""
        import dataclasses
        current = dataclasses.asdict(self)
        for k, v in kwargs.items():
            if v is not None:
                current[k] = v
        return VertexConfig(**current)

    def validate(self) -> None:
        """Raise ValueError for missing required configuration."""
        if not self.project_id:
            raise ValueError(
                "M2C_PROJECT_ID is required. "
                "Set it in your environment or .env file."
            )
        if self.project_id.startswith("your-") or len(self.project_id) < 4:
            raise ValueError(
                f"检测到异常的 Project ID: '{self.project_id}'，请检查 .env 文件"
            )
        valid_ratios = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
        if self.aspect_ratio not in valid_ratios:
            raise ValueError(
                f"Invalid aspect_ratio '{self.aspect_ratio}'. "
                f"Must be one of: {sorted(valid_ratios)}"
            )
