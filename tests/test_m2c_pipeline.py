import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from m2c_pipeline.config import VertexConfig
from m2c_pipeline.pipeline import M2CPipeline
from m2c_pipeline.run_artifacts import RunArtifacts
from m2c_pipeline.translator import ImagePrompt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_INPUT = PROJECT_ROOT / "tests" / "fixtures" / "test_input.md"


def build_png_bytes() -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        image = Image.new("RGB", (16, 16), color="white")
        image.save(tmp.name, format="PNG")
        return Path(tmp.name).read_bytes()


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

    def test_successful_run_writes_block_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            config = VertexConfig(
                project_id="demo-project",
                output_dir=str(output_dir),
                output_format="webp",
                max_workers=1,
            )
            run_artifacts = RunArtifacts(
                config,
                argv=["python", "-m", "m2c_pipeline", str(FIXTURE_INPUT)],
                input_path=str(FIXTURE_INPUT),
                dry_run=False,
            )
            pipeline = M2CPipeline(config, run_artifacts=run_artifacts)
            translator = Mock()
            translator.translate.side_effect = (
                lambda block: ImagePrompt(
                    prompt_text=f"prompt for block {block.index}",
                    aspect_ratio="1:1",
                    source_block=block,
                    model_response_text="ASPECT_RATIO: 1:1\ntranslated prompt",
                    translation_request_text="Translate this Mermaid block",
                    translation_backend="vertex",
                    translation_used_fallback=False,
                    translation_retry_events=(
                        {
                            "attempt": 1,
                            "sleep_seconds": 2.0,
                            "status_code": "429",
                            "error_type": "ClientError",
                            "error_message": "Resource exhausted",
                            "quota_type": "RPM (requests-per-minute burst limit)",
                        },
                    ),
                )
            )
            painter = Mock()
            painter.paint.return_value = build_png_bytes()
            painter.consume_last_result.return_value = {
                "retry_events": [
                    {
                        "attempt": 1,
                        "sleep_seconds": 2.0,
                        "status_code": "429",
                        "error_type": "ClientError",
                        "error_message": "Resource exhausted",
                        "quota_type": "RPM (requests-per-minute burst limit)",
                    }
                ],
                "candidate_image_count": 2,
                "selected_candidate_index": 1,
                "selection_method": "vision_selector",
            }

            with patch.object(pipeline, "_get_translator", return_value=translator):
                with patch.object(pipeline, "_get_painter", return_value=painter):
                    saved = pipeline.run(str(FIXTURE_INPUT), dry_run=False)

            run_artifacts.finalize(status="completed", total_duration_ms=1, saved_paths=saved)

            self.assertEqual(len(saved), 2)
            self.assertTrue(run_artifacts.input_snapshot_path.exists())

            run_manifest = json.loads(
                run_artifacts.run_manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(run_manifest["status"], "completed")
            self.assertEqual(run_manifest["summary"]["saved_count"], 2)
            self.assertEqual(run_manifest["summary"]["failed_count"], 0)
            self.assertEqual(len(run_manifest["blocks"]), 2)

            block_dir = next(run_artifacts.blocks_dir.glob("block_00_*"))
            block_manifest = json.loads((block_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(block_manifest["status"], "succeeded")
            self.assertEqual(block_manifest["block"]["index"], 0)
            self.assertEqual(block_manifest["translation"]["backend_used"], "vertex")
            self.assertEqual(block_manifest["translation"]["retry_count"], 1)
            self.assertEqual(block_manifest["paint"]["retry_count"], 1)
            self.assertEqual(block_manifest["paint"]["candidate_image_count"], 2)
            self.assertEqual(block_manifest["paint"]["selected_candidate_index"], 1)
            self.assertEqual(block_manifest["paint"]["selection_method"], "vision_selector")
            self.assertTrue((block_dir / "mermaid.mmd").exists())
            self.assertTrue((block_dir / "prompt.txt").exists())
            self.assertTrue((block_dir / "translation-request.txt").exists())
            self.assertTrue((block_dir / "translation-response.txt").exists())
            self.assertTrue((block_dir / "result.webp").exists())
            self.assertTrue((block_dir / "result.metadata.json").exists())
            self.assertEqual(block_manifest["output"]["format"], "webp")
            self.assertTrue(Path(block_manifest["output"]["primary_metadata_path"]).exists())
            self.assertTrue(Path(block_manifest["output"]["artifact_metadata_path"]).exists())
            self.assertEqual(
                Path(block_manifest["output"]["primary_path"]).stat().st_size,
                block_manifest["output"]["file_size_bytes"],
            )

    def test_failed_paint_writes_failed_prompt_and_error_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            config = VertexConfig(
                project_id="demo-project",
                output_dir=str(output_dir),
                max_workers=1,
            )
            run_artifacts = RunArtifacts(
                config,
                argv=["python", "-m", "m2c_pipeline", str(FIXTURE_INPUT)],
                input_path=str(FIXTURE_INPUT),
                dry_run=False,
            )
            pipeline = M2CPipeline(config, run_artifacts=run_artifacts)
            translator = Mock()
            translator.translate.side_effect = (
                lambda block: ImagePrompt(
                    prompt_text=f"prompt for block {block.index}",
                    aspect_ratio="1:1",
                    source_block=block,
                    translation_backend="fallback",
                    translation_used_fallback=True,
                    translation_fallback_reason="forced fallback",
                )
            )
            painter = Mock()
            painter.paint.side_effect = RuntimeError("image model quota exhausted")
            painter.consume_last_result.return_value = {
                "retry_events": [
                    {
                        "attempt": 1,
                        "sleep_seconds": 2.0,
                        "status_code": "429",
                        "error_type": "RuntimeError",
                        "error_message": "image model quota exhausted",
                        "quota_type": "RPM (requests-per-minute burst limit)",
                    }
                ],
                "candidate_image_count": None,
                "selected_candidate_index": None,
                "selection_method": None,
            }

            with patch.object(pipeline, "_get_translator", return_value=translator):
                with patch.object(pipeline, "_get_painter", return_value=painter):
                    saved = pipeline.run(str(FIXTURE_INPUT), dry_run=False)

            run_artifacts.finalize(status="completed", total_duration_ms=1, saved_paths=saved)

            self.assertEqual(saved, [])
            failed_prompts = sorted(output_dir.glob("*_FAILED.txt"))
            self.assertEqual(len(failed_prompts), 2)

            run_manifest = json.loads(
                run_artifacts.run_manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual(run_manifest["status"], "completed_with_failures")
            self.assertEqual(run_manifest["summary"]["failed_count"], 2)

            block_dir = next(run_artifacts.blocks_dir.glob("block_00_*"))
            block_manifest = json.loads((block_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(block_manifest["status"], "failed")
            self.assertEqual(block_manifest["failure"]["stage"], "paint")
            self.assertTrue((block_dir / "prompt.txt").exists())
            self.assertTrue((block_dir / "mermaid.mmd").exists())
            self.assertTrue((block_dir / "error.txt").exists())
            self.assertIn("image model quota exhausted", (block_dir / "error.txt").read_text(encoding="utf-8"))
            self.assertTrue(
                Path(block_manifest["files"]["legacy_failed_prompt_path"]).exists()
            )
