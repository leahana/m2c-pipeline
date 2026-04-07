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

    def make_block(self, source: str, diagram_type: str = "flowchart") -> MermaidBlock:
        return MermaidBlock(
            index=0,
            source=source,
            diagram_type=diagram_type,
            line_number=3,
        )

    def make_translator(self, mode: str = "vertex") -> MermaidTranslator:
        config = VertexConfig(project_id="demo-project", translation_mode=mode)
        return MermaidTranslator(config, self.template)

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
        translator = self.make_translator()

        with patch.object(
            MermaidTranslator,
            "_init_client",
            side_effect=ImportError("google-genai package not found. Run: pip install google-genai"),
        ):
            with self.assertRaises(ImportError):
                translator.translate(self.block)

    def test_simple_linear_three_node_graph_is_classified(self) -> None:
        translator = self.make_translator()
        block = self.make_block(
            "flowchart LR\n"
            "A[Install dependencies] --> B[Run bootstrap]\n"
            "B --> C[Dry run m2c_pipeline]"
        )

        analysis = translator._analyze_diagram(block.source, block.diagram_type)

        self.assertTrue(analysis.is_simple_linear)
        self.assertEqual(analysis.simple_linear_order, ["A", "B", "C"])

    def test_branching_graph_is_not_classified_as_simple_linear(self) -> None:
        translator = self.make_translator()
        block = self.make_block(
            "flowchart LR\n"
            "A[开始] --> B[路径一]\n"
            "A --> C[路径二]"
        )

        analysis = translator._analyze_diagram(block.source, block.diagram_type)

        self.assertFalse(analysis.is_simple_linear)

    def test_self_loop_and_four_node_chain_are_not_simple_linear(self) -> None:
        translator = self.make_translator()
        self_loop = self.make_block("flowchart LR\nA[开始] --> A[开始]")
        four_node_chain = self.make_block(
            "flowchart LR\n"
            "A[一] --> B[二]\n"
            "B --> C[三]\n"
            "C --> D[四]"
        )

        self.assertFalse(
            translator._analyze_diagram(self_loop.source, self_loop.diagram_type).is_simple_linear
        )
        self.assertFalse(
            translator._analyze_diagram(
                four_node_chain.source,
                four_node_chain.diagram_type,
            ).is_simple_linear
        )

    def test_simple_linear_three_node_assignment_uses_three_unique_characters(self) -> None:
        translator = self.make_translator()
        assignments = translator._assign_characters(
            "flowchart LR\n"
            "A[Install dependencies] --> B[Run bootstrap]\n"
            "B --> C[Dry run m2c_pipeline]",
            "flowchart",
        )

        self.assertEqual(
            assignments,
            [
                ("A", "Install dependencies", "Chiikawa (吉伊)", "initiator"),
                ("B", "Run bootstrap", "Hachiware (小八)", ""),
                ("C", "Dry run m2c_pipeline", "Usagi (乌萨奇)", "conclusion"),
            ],
        )

    def test_simple_linear_diamond_keeps_hachiware_in_the_middle(self) -> None:
        translator = self.make_translator()
        assignments = translator._assign_characters(
            "flowchart LR\n"
            "A[开始] --> B{\"判断\"}\n"
            "B --> C[完成]",
            "flowchart",
        )

        self.assertEqual(assignments[1], ("B", "判断", "Hachiware (小八)", "decision"))

    def test_non_simple_graph_introduces_three_characters_before_reuse(self) -> None:
        translator = self.make_translator()
        assignments = translator._assign_characters(
            "flowchart LR\n"
            "A[一] --> B[二]\n"
            "B --> C[三]\n"
            "C --> D[四]",
            "flowchart",
        )

        self.assertEqual([item[2] for item in assignments[:4]], [
            "Chiikawa (吉伊)",
            "Hachiware (小八)",
            "Usagi (乌萨奇)",
            "Chiikawa (吉伊)",
        ])

    def test_user_message_for_simple_linear_graph_includes_exactly_three_rule(self) -> None:
        translator = self.make_translator()
        block = self.make_block(
            "flowchart LR\n"
            "A[Install dependencies] --> B[Run bootstrap]\n"
            "B --> C[Dry run m2c_pipeline]"
        )

        user_message = translator._build_user_message(block)

        self.assertIn("## Graph Classification", user_message)
        self.assertIn("Use exactly 3 different main characters", user_message)

    def test_user_message_for_non_simple_graph_drops_parallel_branch_promise(self) -> None:
        translator = self.make_translator()
        block = self.make_block(
            "flowchart LR\n"
            "A[开始] --> B[路径一]\n"
            "A --> C[路径二]"
        )

        user_message = translator._build_user_message(block)

        self.assertIn(
            "prefer introducing all three main characters before any reuse",
            user_message,
        )
        self.assertNotIn("parallel branches", user_message)


class ChiikawaTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = get_template("chiikawa")

    def test_system_instruction_contains_no_japanese_script(self) -> None:
        instruction = self.template.get_system_instruction()

        self.assertNotRegex(instruction, r"[\u3040-\u30ff]")
        self.assertNotIn("ちいかわ", instruction)
        self.assertNotIn("ナガノ", instruction)
        self.assertIn(
            "MAIN CONTENT MUST have exactly 3 major sections",
            instruction,
        )

    def test_fallback_prompt_contains_no_old_japanese_terms(self) -> None:
        prompt = self.template.build_prompt(
            topic="flowchart diagram",
            mermaid_source=(
                "flowchart LR\n"
                "A[Install dependencies] --> B[Run bootstrap]\n"
                "B --> C[Dry run m2c_pipeline]"
            ),
            aspect_ratio="1:1",
        )

        self.assertNotRegex(prompt, r"[\u3040-\u30ff]")
        self.assertNotIn("ちいかわ", prompt)
        self.assertNotIn("ナガノ", prompt)
        self.assertIn("exactly three distinct main characters", prompt)
        self.assertIn("Keep each character visually distinct", prompt)
