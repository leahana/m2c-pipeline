import builtins
import unittest
from unittest.mock import patch

from m2c_pipeline.config import VertexConfig
from m2c_pipeline.extractor import MermaidBlock
from m2c_pipeline.templates import get_template
from m2c_pipeline.translator import MermaidTranslator


class MermaidTranslatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.block = MermaidBlock(
            index=0,
            source="flowchart LR\nA[开始] --> B[结束]",
            diagram_type="flowchart",
            line_number=3,
        )
        self.template = get_template("chiikawa")

    def test_fallback_translate_does_not_initialize_client(self) -> None:
        config = VertexConfig(project_id="", translation_mode="fallback")
        translator = MermaidTranslator(config, self.template)

        with patch.object(
            MermaidTranslator,
            "_init_client",
            side_effect=AssertionError("fallback mode must not initialize the client"),
        ):
            prompt = translator.translate(self.block)

        self.assertEqual(prompt.aspect_ratio, "1:1")
        self.assertIn("Chiikawa", prompt.prompt_text)

    def test_fallback_translate_does_not_import_google(self) -> None:
        config = VertexConfig(project_id="", translation_mode="fallback")
        translator = MermaidTranslator(config, self.template)
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith("google"):
                raise ImportError("google imports should not happen in fallback mode")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            prompt = translator.translate(self.block)

        self.assertIn("Chiikawa", prompt.prompt_text)

    def test_vertex_dependency_error_is_not_swallowed(self) -> None:
        config = VertexConfig(project_id="demo-project", translation_mode="vertex")
        translator = MermaidTranslator(config, self.template)

        with patch.object(
            MermaidTranslator,
            "_init_client",
            side_effect=ImportError("google-genai package not found. Run: pip install google-genai"),
        ):
            with self.assertRaises(ImportError):
                translator.translate(self.block)
