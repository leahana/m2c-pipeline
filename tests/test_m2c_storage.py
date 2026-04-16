import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from m2c_pipeline.config import VertexConfig
from m2c_pipeline.extractor import MermaidBlock
from m2c_pipeline.storage import ImageStorage


def build_image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (16, 16), color="white")
    image.save(buffer, format=image_format)
    return buffer.getvalue()


class ImageStorageTests(unittest.TestCase):
    def test_save_writes_webp_with_sidecar_metadata_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VertexConfig(project_id="demo-project", output_dir=tmpdir)
            storage = ImageStorage(config)
            block = MermaidBlock(
                index=0,
                source="flowchart LR\nA[开始] --> B[结束]",
                diagram_type="flowchart",
                line_number=3,
            )

            saved_path = storage.save(
                build_image_bytes("PNG"),
                block,
                "demo prompt",
                aspect_ratio="1:1",
            )

            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".webp")
            with Image.open(saved_path) as image:
                self.assertEqual(image.format, "WEBP")

            metadata_path = saved_path.with_suffix(".metadata.json")
            self.assertTrue(metadata_path.exists())
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["mermaid_source"], block.source)
            self.assertEqual(metadata["image_prompt"], "demo prompt")
            self.assertEqual(metadata["block_index"], 0)
            self.assertEqual(metadata["diagram_type"], "flowchart")
            self.assertEqual(metadata["aspect_ratio"], "1:1")
            self.assertEqual(metadata["source_image_format"], "png")
            self.assertEqual(metadata["output_format"], "webp")
            self.assertEqual(metadata["image_file"], saved_path.name)
            self.assertIn("generated_at", metadata)
            self.assertIn("output_image_bytes", metadata)

    def test_save_png_writes_embedded_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VertexConfig(
                project_id="demo-project",
                output_dir=tmpdir,
                output_format="png",
            )
            storage = ImageStorage(config)
            block = MermaidBlock(
                index=1,
                source="graph TD\nA --> B",
                diagram_type="graph",
                line_number=6,
            )

            saved_path = storage.save(
                build_image_bytes("JPEG"),
                block,
                "png prompt",
                aspect_ratio="4:3",
            )

            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".png")
            self.assertFalse(saved_path.with_suffix(".metadata.json").exists())
            with Image.open(saved_path) as image:
                self.assertEqual(image.info["mermaid_source"], block.source)
                self.assertEqual(image.info["image_prompt"], "png prompt")
                self.assertEqual(image.info["block_index"], "1")
                self.assertEqual(image.info["diagram_type"], "graph")
                self.assertEqual(image.info["aspect_ratio"], "4:3")
                self.assertEqual(image.info["source_image_format"], "jpeg")
                self.assertIn("generated_at", image.info)

    def test_save_webp_cleans_up_partial_outputs_when_sidecar_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VertexConfig(project_id="demo-project", output_dir=tmpdir)
            storage = ImageStorage(config)
            block = MermaidBlock(
                index=2,
                source="graph TD\nA --> B",
                diagram_type="graph",
                line_number=8,
            )

            def fail_after_partial_sidecar(image_path: Path, debug_metadata: dict[str, object]) -> None:
                image_path.with_suffix(".metadata.json").write_text("{\n", encoding="utf-8")
                raise OSError("disk full")

            with patch.object(
                ImageStorage,
                "_write_sidecar_metadata",
                side_effect=fail_after_partial_sidecar,
            ):
                with self.assertRaises(OSError):
                    storage.save(
                        build_image_bytes("PNG"),
                        block,
                        "demo prompt",
                        aspect_ratio="1:1",
                    )

            self.assertEqual(list(Path(tmpdir).iterdir()), [])

    def test_save_failed_prompt_writes_debug_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VertexConfig(project_id="demo-project", output_dir=tmpdir)
            storage = ImageStorage(config)
            block = MermaidBlock(
                index=2,
                source="graph TD\nA --> B",
                diagram_type="graph",
                line_number=8,
            )

            failed_path = storage.save_failed_prompt(block, "failed prompt text")

            self.assertTrue(failed_path.exists())
            content = failed_path.read_text(encoding="utf-8")
            self.assertIn("# Failed image prompt", content)
            self.assertIn("```mermaid", content)
            self.assertIn("failed prompt text", content)


if __name__ == "__main__":
    unittest.main()
