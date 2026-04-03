import tempfile
import unittest
from pathlib import Path

from PIL import Image

from m2c_pipeline.config import VertexConfig
from m2c_pipeline.extractor import MermaidBlock
from m2c_pipeline.storage import ImageStorage


def build_png_bytes() -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        image = Image.new("RGB", (16, 16), color="white")
        image.save(tmp.name, format="PNG")
        return Path(tmp.name).read_bytes()


class ImageStorageTests(unittest.TestCase):
    def test_save_writes_png_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VertexConfig(project_id="demo-project", output_dir=tmpdir)
            storage = ImageStorage(config)
            block = MermaidBlock(
                index=0,
                source="flowchart LR\nA[开始] --> B[结束]",
                diagram_type="flowchart",
                line_number=3,
            )

            saved_path = storage.save(build_png_bytes(), block, "demo prompt")

            self.assertTrue(saved_path.exists())
            with Image.open(saved_path) as image:
                self.assertEqual(image.info["mermaid_source"], block.source)
                self.assertEqual(image.info["image_prompt"], "demo prompt")
                self.assertEqual(image.info["block_index"], "0")
                self.assertEqual(image.info["diagram_type"], "flowchart")
                self.assertIn("generated_at", image.info)

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
