#!/usr/bin/env python3
"""
m2c_pipeline CLI entry point.

Usage:
    python -m m2c_pipeline input.md
    python -m m2c_pipeline input.md --template chiikawa --dry-run
    python -m m2c_pipeline input.md --aspect-ratio 16:9 --output-dir ./results
"""

import argparse
import logging
import sys

from .config import VertexConfig
from .pipeline import M2CPipeline


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m2c_pipeline",
        description="Mermaid-to-Chiikawa: generate Chiikawa illustrations from Mermaid diagrams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Path to the Markdown file containing mermaid code blocks",
    )
    parser.add_argument(
        "--template",
        default=None,
        metavar="NAME",
        help="Style template name (default: chiikawa)",
    )
    parser.add_argument(
        "--aspect-ratio",
        default=None,
        dest="aspect_ratio",
        metavar="RATIO",
        choices=["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        help="Override aspect ratio for all generated images",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        dest="output_dir",
        metavar="DIR",
        help="Directory to save generated images (default: ./output)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and translate only; skip image generation (free to run)",
    )
    parser.add_argument(
        "--max-workers",
        default=None,
        dest="max_workers",
        type=int,
        metavar="N",
        help="Max parallel blocks (default: 2, set 1 to disable concurrency)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    config = VertexConfig.from_env().apply_overrides(
        template_name=args.template,
        aspect_ratio=args.aspect_ratio,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        log_level=args.log_level,
    )

    _setup_logging(config.log_level)
    logger = logging.getLogger("m2c_pipeline")

    try:
        config.validate()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    logger.info("Config loaded (project=%s, template=%s, image_model=%s)",
                config.project_id, config.template_name, config.image_model)

    pipeline = M2CPipeline(config)
    try:
        saved = pipeline.run(input_path=args.input, dry_run=args.dry_run)
    except FileNotFoundError as exc:
        logger.error("Input file error: %s", exc)
        sys.exit(1)

    if saved:
        print("\nGenerated images:")
        for path in saved:
            print(f"  {path}")
    elif not args.dry_run:
        print("No images were saved. Check logs for details.")


if __name__ == "__main__":
    main()
