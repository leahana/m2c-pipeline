"""
M2CPipeline — orchestrates the full Mermaid-to-Chiikawa pipeline.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from .config import VertexConfig
from .extractor import MermaidBlock, MermaidExtractor
from .painter import ImagePainter
from .run_artifacts import RunArtifacts
from .storage import ImageStorage
from .templates import get_template
from .translator import MermaidTranslator


class M2CPipeline:
    """Orchestrate the full Mermaid-to-Chiikawa pipeline."""

    def __init__(
        self,
        config: VertexConfig,
        *,
        run_artifacts: RunArtifacts | None = None,
    ) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._run_artifacts = run_artifacts

        self._template = get_template(config.template_name)
        self._extractor = MermaidExtractor()
        self._translator: MermaidTranslator | None = None
        self._painter: ImagePainter | None = None
        self._storage: ImageStorage | None = None

    def _get_translator(self) -> MermaidTranslator:
        if self._translator is None:
            self._translator = MermaidTranslator(self._config, self._template)
        return self._translator

    def _get_painter(self) -> ImagePainter:
        if self._painter is None:
            self._painter = ImagePainter(self._config)
        return self._painter

    def _get_storage(self) -> ImageStorage:
        if self._storage is None:
            self._storage = ImageStorage(self._config)
        return self._storage

    def run(self, input_path: str, dry_run: bool = False) -> list[Path]:
        """Execute the full pipeline. Returns paths of all saved images.

        Processes blocks concurrently up to config.max_workers in parallel.
        A Semaphore guards the concurrency limit to avoid quota bursts.

        Args:
            input_path: Path to the Markdown file.
            dry_run:    If True, skip image generation and return empty list.
        """
        self._logger.info("=== m2c_pipeline START ===")
        self._logger.info(
            "Input: %s | Template: %s | Dry-run: %s | mode: %s | max_workers: %d",
            input_path,
            self._config.template_name,
            dry_run,
            self._config.translation_mode,
            self._config.max_workers,
        )
        if self._run_artifacts is not None:
            self._run_artifacts.capture_input_snapshot(input_path)
            self._logger.info("Run artifacts: %s", self._run_artifacts.root_dir)

        # Step 1: Extract (always serial, instant)
        extract_started = perf_counter()
        blocks = self._extractor.extract(input_path)
        extract_finished = perf_counter()
        if self._run_artifacts is not None:
            self._run_artifacts.record_extract(
                block_count=len(blocks),
                duration_ms=int(round((extract_finished - extract_started) * 1000)),
            )
        if not blocks:
            self._logger.warning("No mermaid blocks found in %s", input_path)
            return []
        self._logger.info("Extracted %d mermaid block(s)", len(blocks))

        translator = self._get_translator()
        painter = None if dry_run else self._get_painter()
        storage = None if dry_run else self._get_storage()
        if not dry_run:
            preview_hint = (
                " [preview model — check for GA release and remove '-preview' suffix when available]"
                if "preview" in self._config.image_model.lower()
                else ""
            )
            self._logger.info("image_model: %s%s", self._config.image_model, preview_hint)

        saved_paths: list[Path] = []
        lock = threading.Lock()
        semaphore = threading.Semaphore(self._config.max_workers)

        def process_block(block: MermaidBlock) -> Path | None:
            """Translate → Paint → Store one block under semaphore guard."""
            with semaphore:
                block_started = perf_counter()
                block_artifacts = (
                    self._run_artifacts.start_block(block)
                    if self._run_artifacts is not None
                    else None
                )

                try:
                    translate_started = perf_counter()
                    image_prompt = translator.translate(block)
                    translate_finished = perf_counter()
                    if block_artifacts is not None:
                        block_artifacts.record_translation(
                            image_prompt,
                            duration_ms=int(
                                round((translate_finished - translate_started) * 1000)
                            ),
                        )

                    if dry_run:
                        self._logger.info(
                            "[DRY-RUN] Block %d prompt (aspect_ratio=%s):\n%s",
                            block.index,
                            image_prompt.aspect_ratio,
                            image_prompt.prompt_text,
                        )
                        if block_artifacts is not None:
                            block_artifacts.record_dry_run()
                            block_artifacts.finalize(
                                status="dry_run",
                                total_duration_ms=int(
                                    round((perf_counter() - block_started) * 1000)
                                ),
                            )
                        return None

                    paint_started = perf_counter()
                    try:
                        image_bytes = painter.paint(image_prompt)
                        paint_diagnostics = painter.consume_last_result()
                    except ImportError:
                        raise
                    except Exception as exc:
                        paint_diagnostics = painter.consume_last_result()
                        self._logger.error(
                            "Image generation failed for block %d: %s", block.index, exc
                        )
                        failed_prompt_path = storage.save_failed_prompt(
                            block,
                            image_prompt.prompt_text,
                        )
                        if block_artifacts is not None:
                            block_artifacts.record_paint_failure(
                                exc=exc,
                                duration_ms=int(
                                    round((perf_counter() - paint_started) * 1000)
                                ),
                                diagnostics=paint_diagnostics,
                                failed_prompt_path=failed_prompt_path,
                            )
                            block_artifacts.finalize(
                                status="failed",
                                total_duration_ms=int(
                                    round((perf_counter() - block_started) * 1000)
                                ),
                            )
                        return None

                    if block_artifacts is not None:
                        block_artifacts.record_paint_success(
                            duration_ms=int(
                                round((perf_counter() - paint_started) * 1000)
                            ),
                            image_byte_count=len(image_bytes),
                            diagnostics=paint_diagnostics,
                        )

                    store_started = perf_counter()
                    path = storage.save(
                        image_bytes,
                        block,
                        image_prompt.prompt_text,
                        aspect_ratio=image_prompt.aspect_ratio,
                    )
                    if block_artifacts is not None:
                        block_artifacts.record_storage(
                            primary_path=path,
                            duration_ms=int(
                                round((perf_counter() - store_started) * 1000)
                            ),
                        )
                        block_artifacts.finalize(
                            status="succeeded",
                            total_duration_ms=int(
                                round((perf_counter() - block_started) * 1000)
                            ),
                        )
                    return path
                except ImportError:
                    raise
                except Exception as exc:
                    self._logger.error("Block %d unhandled error: %s", block.index, exc)
                    if block_artifacts is not None:
                        block_artifacts.record_unhandled_failure(
                            stage="pipeline",
                            exc=exc,
                        )
                        block_artifacts.finalize(
                            status="failed",
                            total_duration_ms=int(
                                round((perf_counter() - block_started) * 1000)
                            ),
                        )
                    return None

        # Step 2-4: Process blocks concurrently with tqdm progress bar
        bar_fmt = "{l_bar}{bar}| {n_fmt}/{total_fmt} blocks [{elapsed}<{remaining}]"
        with logging_redirect_tqdm():
            with tqdm(
                total=len(blocks),
                desc="Generating",
                unit="block",
                bar_format=bar_fmt,
                ncols=88,
            ) as pbar:
                with ThreadPoolExecutor(max_workers=self._config.max_workers) as executor:
                    futures = {
                        executor.submit(process_block, block): block
                        for block in blocks
                    }
                    for future in as_completed(futures):
                        block = futures[future]
                        try:
                            path = future.result()
                        except ImportError:
                            raise

                        if path:
                            with lock:
                                saved_paths.append(path)
                            pbar.set_postfix_str(f"#{block.index} ✓ {path.name}")
                        else:
                            pbar.set_postfix_str(
                                f"#{block.index} {'skipped' if dry_run else '✗ failed'}"
                            )
                        pbar.update(1)

        self._logger.info(
            "=== m2c_pipeline DONE — %d image(s) saved ===", len(saved_paths)
        )
        return saved_paths
