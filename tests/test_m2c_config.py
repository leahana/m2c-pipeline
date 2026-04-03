import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from m2c_pipeline.config import VertexConfig


class VertexConfigTests(unittest.TestCase):
    def test_from_env_reads_project_and_models(self) -> None:
        env = {
            "M2C_PROJECT_ID": "demo-project",
            "M2C_LOCATION": "us-central1",
            "M2C_GEMINI_MODEL": "gemini-demo",
            "M2C_IMAGE_MODEL": "image-demo",
            "M2C_ASPECT_RATIO": "16:9",
            "M2C_OUTPUT_DIR": "./custom-output",
            "M2C_TEMPLATE": "chiikawa",
            "M2C_TRANSLATION_MODE": "vertex",
            "M2C_MAX_WORKERS": "3",
            "M2C_REQUEST_TIMEOUT": "120",
            "M2C_MAX_RETRIES": "4",
            "M2C_RETRY_MIN_WAIT": "1",
            "M2C_RETRY_MAX_WAIT": "9",
            "M2C_LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env, clear=False):
            config = VertexConfig.from_env()

        self.assertEqual(config.project_id, "demo-project")
        self.assertEqual(config.gemini_model, "gemini-demo")
        self.assertEqual(config.image_model, "image-demo")
        self.assertEqual(config.aspect_ratio, "16:9")
        self.assertEqual(config.output_dir, "./custom-output")
        self.assertEqual(config.max_workers, 3)
        self.assertEqual(config.request_timeout, 120)
        self.assertEqual(config.max_retries, 4)
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.translation_mode, "vertex")

    def test_apply_overrides_updates_non_none_values(self) -> None:
        config = VertexConfig(project_id="demo-project", aspect_ratio="1:1")

        updated = config.apply_overrides(aspect_ratio="9:16", log_level="WARNING")

        self.assertEqual(updated.project_id, "demo-project")
        self.assertEqual(updated.aspect_ratio, "9:16")
        self.assertEqual(updated.log_level, "WARNING")

    def test_validate_requires_project_id(self) -> None:
        config = VertexConfig(project_id="")

        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_rejects_invalid_ratio(self) -> None:
        config = VertexConfig(project_id="demo-project", aspect_ratio="7:3")

        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_accepts_supported_ratio(self) -> None:
        config = VertexConfig(project_id="demo-project", aspect_ratio="4:3")

        config.validate()

    def test_validate_fallback_requires_dry_run(self) -> None:
        config = VertexConfig(project_id="", translation_mode="fallback")

        with self.assertRaises(ValueError):
            config.validate()

    def test_validate_fallback_allows_missing_project_for_dry_run(self) -> None:
        config = VertexConfig(project_id="", translation_mode="fallback")

        config.validate(dry_run=True)

    def test_from_env_loads_dotenv_from_cwd(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            Path(".env").write_text(
                "M2C_PROJECT_ID=dotenv-project\n"
                "M2C_MAX_WORKERS=7\n",
                encoding="utf-8",
            )
            try:
                with patch.dict(os.environ, {}, clear=True):
                    config = VertexConfig.from_env()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(config.project_id, "dotenv-project")
        self.assertEqual(config.max_workers, 7)


if __name__ == "__main__":
    unittest.main()
