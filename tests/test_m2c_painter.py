import unittest
from unittest.mock import Mock, patch

from m2c_pipeline.config import VertexConfig
from m2c_pipeline.extractor import MermaidBlock
from m2c_pipeline.painter import ImagePainter
from m2c_pipeline.translator import ImagePrompt


class ImagePainterTests(unittest.TestCase):
    def make_prompt(self) -> ImagePrompt:
        block = MermaidBlock(
            index=0,
            source="flowchart LR\nA[开始] --> B[结束]",
            diagram_type="flowchart",
            line_number=3,
        )
        return ImagePrompt(
            prompt_text="demo prompt",
            aspect_ratio="1:1",
            source_block=block,
        )

    def test_paint_raises_when_no_candidates_returned(self) -> None:
        painter = ImagePainter(VertexConfig(project_id="demo-project"))
        prompt = self.make_prompt()

        with patch.object(ImagePainter, "_call_gemini", return_value=[]):
            with self.assertRaises(RuntimeError):
                painter.paint(prompt)

        diagnostics = painter.consume_last_result()
        self.assertEqual(diagnostics["candidate_image_count"], 0)
        self.assertIsNone(diagnostics["selected_candidate_index"])
        self.assertEqual(diagnostics["selection_method"], "no_candidates_returned")
        self.assertIsNone(diagnostics["selector_seed"])

    def test_paint_uses_selected_candidate_when_selector_succeeds(self) -> None:
        painter = ImagePainter(
            VertexConfig(project_id="demo-project", image_candidate_count=2, translation_seed=42)
        )
        prompt = self.make_prompt()

        with patch.object(
            ImagePainter,
            "_call_gemini",
            return_value=[b"first-image", b"second-image"],
        ):
            with patch.object(ImagePainter, "_select_best_candidate", return_value=1):
                image_bytes = painter.paint(prompt)

        self.assertEqual(image_bytes, b"second-image")
        diagnostics = painter.consume_last_result()
        self.assertEqual(diagnostics["candidate_image_count"], 2)
        self.assertEqual(diagnostics["selected_candidate_index"], 1)
        self.assertEqual(diagnostics["selection_method"], "vision_selector")
        self.assertEqual(diagnostics["selector_seed"], 42)

    def test_paint_falls_back_to_first_candidate_when_selector_fails(self) -> None:
        painter = ImagePainter(
            VertexConfig(project_id="demo-project", image_candidate_count=2)
        )
        prompt = self.make_prompt()

        with patch.object(
            ImagePainter,
            "_call_gemini",
            return_value=[b"first-image", b"second-image"],
        ):
            with patch.object(
                ImagePainter,
                "_select_best_candidate",
                side_effect=RuntimeError("selector unavailable"),
            ):
                image_bytes = painter.paint(prompt)

        self.assertEqual(image_bytes, b"first-image")
        diagnostics = painter.consume_last_result()
        self.assertEqual(diagnostics["candidate_image_count"], 2)
        self.assertEqual(diagnostics["selected_candidate_index"], 0)
        self.assertTrue(
            diagnostics["selection_method"].startswith("fallback_first_candidate_after_")
        )

    def test_paint_skips_selector_when_only_one_candidate_is_returned(self) -> None:
        painter = ImagePainter(VertexConfig(project_id="demo-project"))
        prompt = self.make_prompt()

        with patch.object(ImagePainter, "_call_gemini", return_value=[b"only-image"]):
            with patch.object(ImagePainter, "_select_best_candidate") as selector:
                image_bytes = painter.paint(prompt)

        self.assertEqual(image_bytes, b"only-image")
        selector.assert_not_called()
        diagnostics = painter.consume_last_result()
        self.assertEqual(diagnostics["candidate_image_count"], 1)
        self.assertEqual(diagnostics["selected_candidate_index"], 0)
        self.assertEqual(diagnostics["selection_method"], "single_candidate")
        self.assertIsNone(diagnostics["selector_seed"])

    def test_call_gemini_passes_size_seed_and_candidate_count(self) -> None:
        config = VertexConfig(
            project_id="demo-project",
            image_model="image-demo",
            image_size="4K",
            image_candidate_count=3,
            image_seed=19,
        )
        painter = ImagePainter(config)

        inline_data = Mock(data=b"demo-image")
        part = Mock(inline_data=inline_data)
        candidate = Mock(content=Mock(parts=[part]))
        fake_response = Mock(candidates=[candidate])
        fake_client = Mock()
        fake_client.models.generate_content.return_value = fake_response

        with patch.object(ImagePainter, "_get_image_client", return_value=fake_client):
            images = painter._call_gemini("demo prompt", "16:9")

        self.assertEqual(images, [b"demo-image"])
        call = fake_client.models.generate_content.call_args
        self.assertEqual(call.kwargs["model"], "image-demo")
        self.assertEqual(call.kwargs["contents"], "demo prompt")
        config_payload = call.kwargs["config"]
        self.assertEqual(config_payload.candidate_count, 3)
        self.assertEqual(config_payload.seed, 19)
        self.assertEqual(config_payload.image_config.aspect_ratio, "16:9")
        self.assertEqual(config_payload.image_config.image_size, "4K")

    def test_parse_best_index_rejects_invalid_selector_response(self) -> None:
        with self.assertRaises(ValueError):
            ImagePainter._parse_best_index("choose candidate two", 2)


if __name__ == "__main__":
    unittest.main()
