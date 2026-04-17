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
from time import perf_counter

from .config import (
    VALID_ASPECT_RATIOS,
    VALID_OUTPUT_FORMATS,
    VALID_TRANSLATION_MODES,
    VertexConfig,
)
from .pipeline import M2CPipeline
from .run_artifacts import RunArtifacts
from .version import __version__

MINIMUM_PYTHON = (3, 11)
_ARG_UNSET = object()


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


def _setup_logging(level: str, *, log_file: str | None = None) -> logging.Handler | None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    file_handler: logging.Handler | None = None
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        handlers.append(file_handler)

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True,
    )
    return file_handler


def _optional_int_arg(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized in {"none", "off", "random", "unset"}:
        return None
    return int(value)


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
        "--output-format",
        default=None,
        dest="output_format",
        metavar="FMT",
        choices=list(VALID_OUTPUT_FORMATS),
        help="Saved image format (default: webp)",
    )
    parser.add_argument(
        "--translation-seed",
        default=_ARG_UNSET,
        dest="translation_seed",
        type=_optional_int_arg,
        metavar="SEED|random",
        help="Seed for prompt translation. Use 'random' to disable fixed seeding.",
    )
    parser.add_argument(
        "--translation-temperature",
        default=None,
        dest="translation_temperature",
        type=float,
        metavar="FLOAT",
        help="Temperature for Mermaid-to-prompt translation (default: 0.1)",
    )
    parser.add_argument(
        "--translation-top-p",
        default=None,
        dest="translation_top_p",
        type=float,
        metavar="FLOAT",
        help="Top-p for Mermaid-to-prompt translation (default: 0.2)",
    )
    parser.add_argument(
        "--webp-quality",
        default=None,
        dest="webp_quality",
        type=int,
        metavar="N",
        help="WebP quality for saved images, 0-100 (default: 85)",
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
    run_started = perf_counter()
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
        output_format=args.output_format,
        translation_temperature=args.translation_temperature,
        translation_top_p=args.translation_top_p,
        webp_quality=args.webp_quality,
        max_workers=args.max_workers,
        log_level=args.log_level,
    )

    if args.translation_seed is not _ARG_UNSET:
        config.translation_seed = args.translation_seed
    # Validate config before touching the filesystem so that dry-runs and
    # config errors never require a writable output directory.
    try:
        config.validate(dry_run=args.dry_run)
    except ValueError as exc:
        print(f"ERROR: Configuration error: {exc}", file=sys.stderr)
        return 1

    effective_argv = argv if argv is not None else sys.argv[1:]
    try:
        run_artifacts = RunArtifacts(
            config,
            argv=["python", "-m", "m2c_pipeline", *effective_argv],
            input_path=args.input,
            dry_run=args.dry_run,
        )
    except OSError as exc:
        print(
            f"ERROR: Cannot create run artifacts in '{config.output_dir}': {exc}",
            file=sys.stderr,
        )
        return 1

    file_handler = _setup_logging(config.log_level, log_file=str(run_artifacts.run_log_path))
    logger = logging.getLogger("m2c_pipeline")

    try:

        logger.info(
            "Config loaded (mode=%s, project=%s, template=%s, image_model=%s)",
            config.translation_mode,
            config.project_id or "n/a",
            config.template_name,
            config.image_model,
        )

        try:
            pipeline = M2CPipeline(config, run_artifacts=run_artifacts)
            saved = pipeline.run(input_path=args.input, dry_run=args.dry_run)
        except ImportError as exc:
            logger.error("Dependency error: %s", exc)
            run_artifacts.finalize(
                status="failed",
                total_duration_ms=int(round((perf_counter() - run_started) * 1000)),
                saved_paths=[],
                error=exc,
            )
            return 1
        except KeyError as exc:
            logger.error("Template error: %s", exc)
            run_artifacts.finalize(
                status="failed",
                total_duration_ms=int(round((perf_counter() - run_started) * 1000)),
                saved_paths=[],
                error=exc,
            )
            return 1
        except FileNotFoundError as exc:
            logger.error("Input file error: %s", exc)
            run_artifacts.finalize(
                status="failed",
                total_duration_ms=int(round((perf_counter() - run_started) * 1000)),
                saved_paths=[],
                error=exc,
            )
            return 1

        run_artifacts.finalize(
            status="completed",
            total_duration_ms=int(round((perf_counter() - run_started) * 1000)),
            saved_paths=saved,
        )

        if saved:
            print("\nGenerated images:")
            for path in saved:
                print(f"  {path}")
        elif args.dry_run:
            print("Dry run completed successfully.")
        elif not args.dry_run:
            print("No images were saved. Check logs for details.")
        return 0
    finally:
        if file_handler is not None:
            root_logger = logging.getLogger()
            root_logger.removeHandler(file_handler)
            file_handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
