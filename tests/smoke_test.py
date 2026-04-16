#!/usr/bin/env python3
"""
Manual integration smoke test for `m2c_pipeline`.

This file keeps the historical name `test_sdk_migration.py`, but it is not a
unit test module. Run it directly when you want a real end-to-end check against
Vertex AI:

    python tests/test_sdk_migration.py --input tests/fixtures/test_input.md
    python tests/test_sdk_migration.py --input tests/fixtures/test_input.md --with-image
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INPUT = PROJECT_ROOT / "tests" / "fixtures" / "test_input.md"
OUTPUT_DIR = PROJECT_ROOT / "tests" / "output"
PROMPT_REPORT = OUTPUT_DIR / "translated_prompts.md"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("test_sdk_migration")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual integration smoke test for m2c_pipeline.",
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Markdown file containing mermaid blocks.",
    )
    parser.add_argument(
        "--with-image",
        action="store_true",
        help="Generate one real image after translating all blocks.",
    )
    return parser


def ensure_env() -> str:
    project_id = os.environ.get("M2C_PROJECT_ID", "").strip()
    if not project_id:
        raise SystemExit(
            "M2C_PROJECT_ID is not set. Load .env or export it before running this script."
        )
    return project_id


def translate_input(input_path: Path):
    from m2c_pipeline.config import VertexConfig
    from m2c_pipeline.extractor import MermaidExtractor
    from m2c_pipeline.templates import get_template
    from m2c_pipeline.translator import MermaidTranslator

    config = VertexConfig.from_env()
    extractor = MermaidExtractor()
    template = get_template(config.template_name)
    translator = MermaidTranslator(config, template)

    blocks = extractor.extract(str(input_path))
    if not blocks:
        raise SystemExit(f"No mermaid blocks found in {input_path}")

    prompts = []
    for block in blocks:
        logger.info("Translating block %d (type=%s)", block.index, block.diagram_type)
        prompts.append(translator.translate(block))
    return prompts


def write_prompt_report(prompts) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = ["# m2c_pipeline translation smoke report", ""]
    for prompt in prompts:
        block = prompt.source_block
        lines.extend(
            [
                f"## Block {block.index}",
                "",
                f"- diagram_type: `{block.diagram_type}`",
                f"- line_number: `{block.line_number}`",
                f"- aspect_ratio: `{prompt.aspect_ratio}`",
                "",
                "### Mermaid",
                "",
                "```mermaid",
                block.source,
                "```",
                "",
                "### Prompt",
                "",
                prompt.prompt_text,
                "",
            ]
        )

    PROMPT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Prompt report saved to %s", PROMPT_REPORT)
    return PROMPT_REPORT


def generate_first_image(prompt) -> Path:
    from PIL import Image

    from m2c_pipeline.config import VertexConfig
    from m2c_pipeline.painter import ImagePainter
    from m2c_pipeline.storage import ImageStorage

    config = VertexConfig.from_env().apply_overrides(output_dir=str(OUTPUT_DIR))
    painter = ImagePainter(config)
    storage = ImageStorage(config)

    logger.info(
        "Generating one image for block %d with model=%s",
        prompt.source_block.index,
        config.image_model,
    )
    image_bytes = painter.paint(prompt)
    image_path = storage.save(image_bytes, prompt.source_block, prompt.prompt_text)

    if image_path.suffix == ".png":
        with Image.open(image_path) as image:
            for key in ("mermaid_source", "image_prompt", "generated_at"):
                if key not in image.info:
                    raise RuntimeError(f"PNG metadata missing required key: {key}")
    else:
        metadata_path = image_path.with_suffix(".metadata.json")
        if not metadata_path.exists():
            raise RuntimeError(f"Metadata sidecar missing: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for key in ("mermaid_source", "image_prompt", "generated_at"):
            if key not in metadata:
                raise RuntimeError(f"Metadata sidecar missing required key: {key}")

    logger.info("Image saved to %s", image_path)
    return image_path


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    project_id = ensure_env()
    logger.info("Using project %s", project_id)

    prompts = translate_input(input_path)
    report_path = write_prompt_report(prompts)

    print()
    print("Translation smoke test passed.")
    print(f"Prompt report: {report_path}")

    if args.with_image:
        image_path = generate_first_image(prompts[0])
        print(f"Generated image: {image_path}")
    else:
        print("Image generation skipped. Re-run with --with-image for a full smoke test.")


if __name__ == "__main__":
    main()
