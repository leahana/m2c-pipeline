"""
Vertex AI configuration management for m2c_pipeline.
All parameters are loaded from environment variables with sensible defaults.
"""

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

VALID_ASPECT_RATIOS = (
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
)
VALID_TRANSLATION_MODES = ("vertex", "fallback")
VALID_OUTPUT_FORMATS = ("png", "webp")
VALID_IMAGE_SIZES = ("1K", "2K", "4K")


def _parse_optional_int(raw_value: str | None, *, default: int | None = None) -> int | None:
    """Parse optional integer values from env/CLI style strings.

    Empty strings and marker values such as "none" / "random" disable the seed.
    """
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if not normalized or normalized in {"none", "off", "random", "unset"}:
        return None
    return int(raw_value)


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
    image_model: str = "gemini-2.5-flash-image"

    # === Image generation params ===
    # Supported values for Gemini image generation models:
    # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
    aspect_ratio: str = "1:1"
    image_size: str = "2K"
    image_candidate_count: int = 1
    image_seed: int | None = 7

    # === Pipeline ===
    output_dir: str = "./output"
    output_format: str = "webp"
    webp_quality: int = 85
    template_name: str = "chiikawa"
    translation_temperature: float = 0.1
    translation_top_p: float = 0.2
    translation_seed: int | None = 7

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
    translation_mode: str = "vertex"

    @classmethod
    def from_env(cls) -> "VertexConfig":
        """Load configuration from M2C_* environment variables."""
        load_local_env()
        return cls(
            project_id=os.environ.get("M2C_PROJECT_ID", ""),
            location=os.environ.get("M2C_LOCATION", "us-central1"),
            gemini_model=os.environ.get("M2C_GEMINI_MODEL", "gemini-2.0-flash"),
            image_model=os.environ.get("M2C_IMAGE_MODEL", "gemini-2.5-flash-image"),
            aspect_ratio=os.environ.get("M2C_ASPECT_RATIO", "1:1"),
            image_size=os.environ.get("M2C_IMAGE_SIZE", "2K"),
            image_candidate_count=int(os.environ.get("M2C_IMAGE_CANDIDATE_COUNT", "1")),
            image_seed=_parse_optional_int(os.environ.get("M2C_IMAGE_SEED"), default=7),
            output_dir=os.environ.get("M2C_OUTPUT_DIR", "./output"),
            output_format=os.environ.get("M2C_OUTPUT_FORMAT", "webp"),
            webp_quality=int(os.environ.get("M2C_WEBP_QUALITY", "85")),
            template_name=os.environ.get("M2C_TEMPLATE", "chiikawa"),
            translation_temperature=float(
                os.environ.get("M2C_TRANSLATION_TEMPERATURE", "0.1")
            ),
            translation_top_p=float(os.environ.get("M2C_TRANSLATION_TOP_P", "0.2")),
            translation_seed=_parse_optional_int(
                os.environ.get("M2C_TRANSLATION_SEED"),
                default=7,
            ),
            max_workers=int(os.environ.get("M2C_MAX_WORKERS", "2")),
            request_timeout=int(os.environ.get("M2C_REQUEST_TIMEOUT", "600")),
            max_retries=int(os.environ.get("M2C_MAX_RETRIES", "5")),
            retry_min_wait=int(os.environ.get("M2C_RETRY_MIN_WAIT", "2")),
            retry_max_wait=int(os.environ.get("M2C_RETRY_MAX_WAIT", "60")),
            log_level=os.environ.get("M2C_LOG_LEVEL", "INFO"),
            translation_mode=os.environ.get("M2C_TRANSLATION_MODE", "vertex"),
        )

    def apply_overrides(self, **kwargs) -> "VertexConfig":
        """Return a new VertexConfig with CLI overrides applied (non-None values only)."""
        import dataclasses
        current = dataclasses.asdict(self)
        for k, v in kwargs.items():
            if v is not None:
                current[k] = v
        return VertexConfig(**current)

    def validate(self, *, dry_run: bool = False) -> None:
        """Raise ValueError for invalid runtime configuration."""
        if self.aspect_ratio not in VALID_ASPECT_RATIOS:
            raise ValueError(
                f"Invalid aspect_ratio '{self.aspect_ratio}'. "
                f"Must be one of: {sorted(VALID_ASPECT_RATIOS)}"
            )
        if self.translation_mode not in VALID_TRANSLATION_MODES:
            raise ValueError(
                f"Invalid translation_mode '{self.translation_mode}'. "
                f"Must be one of: {sorted(VALID_TRANSLATION_MODES)}"
            )
        if self.image_size not in VALID_IMAGE_SIZES:
            raise ValueError(
                f"Invalid image_size '{self.image_size}'. "
                f"Must be one of: {sorted(VALID_IMAGE_SIZES)}"
            )
        if self.output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format '{self.output_format}'. "
                f"Must be one of: {sorted(VALID_OUTPUT_FORMATS)}"
            )
        if not 1 <= self.image_candidate_count <= 4:
            raise ValueError(
                f"Invalid image_candidate_count '{self.image_candidate_count}'. "
                "Must be between 1 and 4."
            )
        if not 0 <= self.webp_quality <= 100:
            raise ValueError(
                f"Invalid webp_quality '{self.webp_quality}'. "
                "Must be between 0 and 100."
            )
        if not 0.0 <= self.translation_temperature <= 2.0:
            raise ValueError(
                f"Invalid translation_temperature '{self.translation_temperature}'. "
                "Must be between 0.0 and 2.0."
            )
        if not 0.0 <= self.translation_top_p <= 1.0:
            raise ValueError(
                f"Invalid translation_top_p '{self.translation_top_p}'. "
                "Must be between 0.0 and 1.0."
            )
        if self.translation_mode == "fallback":
            if not dry_run:
                raise ValueError(
                    "Fallback translation mode only supports --dry-run. "
                    "Use --translation-mode vertex for image generation."
                )
            return
        if not self.project_id:
            raise ValueError(
                "M2C_PROJECT_ID is required for vertex translation mode. "
                "Set it in your environment or .env file."
            )
        if self.project_id.startswith("your-") or len(self.project_id) < 4:
            raise ValueError(
                f"检测到异常的 Project ID: '{self.project_id}'，请检查 .env 文件"
            )
