#!/usr/bin/env python3
"""
m2c_pipeline CLI entry point.

Usage:
    python -m m2c_pipeline input.md
    python -m m2c_pipeline input.md --template chiikawa --dry-run
    python -m m2c_pipeline input.md --aspect-ratio 16:9 --output-dir ./results
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import VALID_ASPECT_RATIOS, VALID_TRANSLATION_MODES, VertexConfig
from .pipeline import M2CPipeline
from .version import __version__

MINIMUM_PYTHON = (3, 11)


def _runtime_python_version() -> tuple[int, int]:
    return sys.version_info[:2]


def _require_supported_python() -> None:
    version = _runtime_python_version()
    if version < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        current = ".".join(str(part) for part in version)
        raise RuntimeError(
            f"m2c_pipeline requires Python {required}+ at runtime; "
            f"current interpreter is {current}. "
            "Recreate the repo-local virtualenv with ./scripts/bootstrap_env.sh."
        )


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
        nargs="?",
        help="Path to the Markdown file containing mermaid code blocks",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
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
        choices=list(VALID_ASPECT_RATIOS),
        help="Override aspect ratio for all generated images",
    )
    parser.add_argument(
        "--translation-mode",
        default=None,
        dest="translation_mode",
        choices=list(VALID_TRANSLATION_MODES),
        help="Translation backend to use (default: vertex)",
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


def main(argv: list[str] | None = None) -> int:
    try:
        _require_supported_python()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.input is None:
        parser.error("the following arguments are required: input")

    config = VertexConfig.from_env().apply_overrides(
        template_name=args.template,
        aspect_ratio=args.aspect_ratio,
        translation_mode=args.translation_mode,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        log_level=args.log_level,
    )

    _setup_logging(config.log_level)
    logger = logging.getLogger("m2c_pipeline")

    try:
        config.validate(dry_run=args.dry_run)
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    logger.info(
        "Config loaded (mode=%s, project=%s, template=%s, image_model=%s)",
        config.translation_mode,
        config.project_id or "n/a",
        config.template_name,
        config.image_model,
    )

    try:
        pipeline = M2CPipeline(config)
        saved = pipeline.run(input_path=args.input, dry_run=args.dry_run)
    except ImportError as exc:
        logger.error("Dependency error: %s", exc)
        return 1
    except KeyError as exc:
        logger.error("Template error: %s", exc)
        return 1
    except FileNotFoundError as exc:
        logger.error("Input file error: %s", exc)
        return 1

    if saved:
        print("\nGenerated images:")
        for path in saved:
            print(f"  {path}")
    elif args.dry_run:
        print("Dry run completed successfully.")
    elif not args.dry_run:
        print("No images were saved. Check logs for details.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
