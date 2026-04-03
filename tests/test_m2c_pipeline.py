import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from m2c_pipeline.config import VertexConfig
from m2c_pipeline.pipeline import M2CPipeline
from m2c_pipeline.translator import ImagePrompt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_INPUT = PROJECT_ROOT / "tests" / "fixtures" / "test_input.md"


class PipelineTests(unittest.TestCase):
    def test_dry_run_does_not_initialize_painter_or_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VertexConfig(
                project_id="",
                translation_mode="fallback",
                output_dir=tmpdir,
            )
            pipeline = M2CPipeline(config)
            translator = Mock()
            translator.translate.side_effect = (
                lambda block: ImagePrompt(
                    prompt_text="demo prompt",
                    aspect_ratio="1:1",
                    source_block=block,
                )
            )

            with patch.object(pipeline, "_get_translator", return_value=translator):
                with patch.object(
                    pipeline,
                    "_get_painter",
                    side_effect=AssertionError("dry-run must not initialize painter"),
                ):
                    with patch.object(
                        pipeline,
                        "_get_storage",
                        side_effect=AssertionError("dry-run must not initialize storage"),
                    ):
                        saved = pipeline.run(str(FIXTURE_INPUT), dry_run=True)

        self.assertEqual(saved, [])
