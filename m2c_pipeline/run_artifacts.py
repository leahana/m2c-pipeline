"""
Run-scoped troubleshooting artifacts for m2c_pipeline.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
import threading
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

from .config import VertexConfig
from .extractor import MermaidBlock

if TYPE_CHECKING:
    from .translator import ImagePrompt


RUN_ARTIFACTS_DIRNAME = "_runs"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    value = value or _utc_now()
    return value.strftime("%Y%m%dT%H%M%S_%fZ")


def _sanitize_for_path(value: str) -> str:
    chars = []
    for char in value.lower():
        if char.isalnum():
            chars.append(char)
        elif char in {"-", "_"}:
            chars.append(char)
        else:
            chars.append("_")
    collapsed = "".join(chars).strip("_")
    return collapsed or "unknown"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _link_or_copy(source: Path, destination: Path) -> str:
    link_mode = "hardlink"
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
        link_mode = "copy"
    return link_mode


def _exception_payload(exc: BaseException) -> dict[str, str]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
    }


def _traceback_text(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


class RunArtifacts:
    """Manage run-level logs and per-block troubleshooting artifacts."""

    def __init__(
        self,
        config: VertexConfig,
        *,
        argv: Sequence[str],
        input_path: str,
        dry_run: bool,
    ) -> None:
        self._config = config
        self._argv = list(argv)
        self._dry_run = dry_run
        self._input_path = input_path
        self._started_at = _utc_now()
        self.run_id = f"run_{_timestamp(self._started_at)}"
        self.root_dir = Path(config.output_dir) / RUN_ARTIFACTS_DIRNAME / self.run_id
        self.logs_dir = self.root_dir / "logs"
        self.blocks_dir = self.root_dir / "blocks"
        self.run_log_path = self.logs_dir / "run.log"
        self.run_manifest_path = self.root_dir / "run.json"
        self.input_snapshot_path = self.root_dir / "input.md"
        self._lock = threading.Lock()
        self._block_summaries: dict[int, dict[str, Any]] = {}

        self.logs_dir.mkdir(parents=True, exist_ok=False)
        self.blocks_dir.mkdir(parents=True, exist_ok=True)
        self._write_run_manifest(status="running")

    def _base_manifest(self) -> dict[str, Any]:
        input_path = Path(self._input_path)
        return {
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._started_at.isoformat(),
            "completed_at": None,
            "dry_run": self._dry_run,
            "command": {
                "argv": self._argv,
                "shell": shlex.join(self._argv),
            },
            "input": {
                "path": str(input_path),
                "absolute_path": str(input_path.resolve(strict=False)),
                "exists": input_path.exists(),
                "snapshot_path": str(self.input_snapshot_path)
                if input_path.exists()
                else None,
            },
            "config": asdict(self._config),
            "environment": {
                "cwd": str(Path.cwd()),
                "python_executable": sys.executable,
                "python_version": sys.version.split()[0],
                "pid": os.getpid(),
                "google_application_credentials": os.environ.get(
                    "GOOGLE_APPLICATION_CREDENTIALS"
                ),
            },
            "artifacts": {
                "root_dir": str(self.root_dir),
                "blocks_dir": str(self.blocks_dir),
                "run_log_path": str(self.run_log_path),
            },
            "timings_ms": {},
            "summary": {
                "block_count": 0,
                "saved_count": 0,
                "failed_count": 0,
                "dry_run_count": 0,
            },
            "saved_image_paths": [],
            "blocks": [],
            "error": None,
        }

    def _load_manifest(self) -> dict[str, Any]:
        return json.loads(self.run_manifest_path.read_text(encoding="utf-8"))

    def _write_run_manifest(self, **updates: Any) -> None:
        payload = self._base_manifest()
        if self.run_manifest_path.exists():
            payload = self._load_manifest()
        payload.update(updates)
        _write_json(self.run_manifest_path, payload)

    def capture_input_snapshot(self, input_path: str) -> Path | None:
        source = Path(input_path)
        if not source.exists():
            return None
        content = source.read_text(encoding="utf-8")
        self.input_snapshot_path.write_text(content, encoding="utf-8")
        self._write_run_manifest(
            input={
                **self._load_manifest()["input"],
                "snapshot_path": str(self.input_snapshot_path),
            }
        )
        return self.input_snapshot_path

    def record_extract(self, *, block_count: int, duration_ms: int) -> None:
        with self._lock:
            manifest = self._load_manifest()
            manifest["timings_ms"]["extract"] = duration_ms
            manifest["summary"]["block_count"] = block_count
            _write_json(self.run_manifest_path, manifest)

    def start_block(self, block: MermaidBlock) -> "BlockArtifacts":
        return BlockArtifacts(self, block)

    def register_block(self, summary: dict[str, Any]) -> None:
        with self._lock:
            self._block_summaries[summary["block_index"]] = summary
            manifest = self._load_manifest()
            manifest["blocks"] = [
                self._block_summaries[index]
                for index in sorted(self._block_summaries)
            ]

            saved_count = sum(
                1 for item in self._block_summaries.values() if item["status"] == "succeeded"
            )
            failed_count = sum(
                1 for item in self._block_summaries.values() if item["status"] == "failed"
            )
            dry_run_count = sum(
                1 for item in self._block_summaries.values() if item["status"] == "dry_run"
            )
            manifest["summary"] = {
                "block_count": len(self._block_summaries),
                "saved_count": saved_count,
                "failed_count": failed_count,
                "dry_run_count": dry_run_count,
            }
            _write_json(self.run_manifest_path, manifest)

    def finalize(
        self,
        *,
        status: str,
        total_duration_ms: int,
        saved_paths: Sequence[Path],
        error: BaseException | None = None,
    ) -> None:
        with self._lock:
            manifest = self._load_manifest()
            manifest["completed_at"] = _utc_now().isoformat()
            manifest["timings_ms"]["total"] = total_duration_ms

            failed_count = manifest["summary"]["failed_count"]
            if status == "completed" and failed_count:
                status = "completed_with_failures"

            manifest["status"] = status
            manifest["saved_image_paths"] = [str(path.resolve()) for path in saved_paths]
            manifest["error"] = _exception_payload(error) if error else None
            _write_json(self.run_manifest_path, manifest)


class BlockArtifacts:
    """Write per-block troubleshooting materials into a self-contained directory."""

    def __init__(self, run_artifacts: RunArtifacts, block: MermaidBlock) -> None:
        self._run_artifacts = run_artifacts
        self._block = block
        dirname = (
            f"block_{block.index:02d}_line_{block.line_number:04d}_"
            f"{_sanitize_for_path(block.diagram_type)}"
        )
        self.block_dir = self._run_artifacts.blocks_dir / dirname
        self.block_dir.mkdir(parents=True, exist_ok=True)

        self.mermaid_path = self.block_dir / "mermaid.mmd"
        self.prompt_path = self.block_dir / "prompt.txt"
        self.translation_request_path = self.block_dir / "translation-request.txt"
        self.translation_response_path = self.block_dir / "translation-response.txt"
        self.result_path: Path | None = None
        self.result_metadata_path: Path | None = None
        self.error_path = self.block_dir / "error.txt"
        self.manifest_path = self.block_dir / "manifest.json"

        self.mermaid_path.write_text(block.source.rstrip() + "\n", encoding="utf-8")
        self._manifest: dict[str, Any] = {
            "run_id": self._run_artifacts.run_id,
            "status": "running",
            "started_at": _utc_now().isoformat(),
            "completed_at": None,
            "input": {
                "path": str(Path(self._run_artifacts._input_path).resolve(strict=False)),
            },
            "block": {
                "index": block.index,
                "line_number": block.line_number,
                "diagram_type": block.diagram_type,
            },
            "files": {
                "artifact_dir": str(self.block_dir),
                "mermaid_source_path": str(self.mermaid_path),
                "prompt_path": None,
                "translation_request_path": None,
                "translation_response_path": None,
                "result_path": None,
                "result_metadata_path": None,
                "legacy_failed_prompt_path": None,
                "error_path": None,
            },
            "config": {
                "translation_mode": self._run_artifacts._config.translation_mode,
                "gemini_model": self._run_artifacts._config.gemini_model,
                "translation_temperature": self._run_artifacts._config.translation_temperature,
                "translation_top_p": self._run_artifacts._config.translation_top_p,
                "translation_seed": self._run_artifacts._config.translation_seed,
                "image_model": self._run_artifacts._config.image_model,
                "image_size": self._run_artifacts._config.image_size,
                "image_candidate_count": self._run_artifacts._config.image_candidate_count,
                "image_seed": self._run_artifacts._config.image_seed,
                "aspect_ratio": self._run_artifacts._config.aspect_ratio,
                "output_format": self._run_artifacts._config.output_format,
                "template_name": self._run_artifacts._config.template_name,
                "max_workers": self._run_artifacts._config.max_workers,
            },
            "timings_ms": {},
            "translation": {
                "status": "pending",
                "mode_requested": self._run_artifacts._config.translation_mode,
                "backend_used": None,
                "model": None,
                "aspect_ratio": None,
                "prompt_length": None,
                "used_fallback": None,
                "fallback_reason": None,
                "retry_count": 0,
                "attempt_count": 0,
                "retry_events": [],
                "temperature": self._run_artifacts._config.translation_temperature,
                "top_p": self._run_artifacts._config.translation_top_p,
                "seed": self._run_artifacts._config.translation_seed,
            },
            "paint": {
                "status": "pending" if not self._run_artifacts._dry_run else "skipped",
                "model": self._run_artifacts._config.image_model
                if not self._run_artifacts._dry_run
                else None,
                "image_size": self._run_artifacts._config.image_size
                if not self._run_artifacts._dry_run
                else None,
                "candidate_count_requested": self._run_artifacts._config.image_candidate_count
                if not self._run_artifacts._dry_run
                else None,
                "seed": self._run_artifacts._config.image_seed
                if not self._run_artifacts._dry_run
                else None,
                "retry_count": 0,
                "attempt_count": 0,
                "retry_events": [],
                "candidate_image_count": None,
                "selected_candidate_index": None,
                "selection_method": None,
                "result_bytes": None,
            },
            "output": {
                "format": None,
                "primary_path": None,
                "artifact_result_path": None,
                "primary_metadata_path": None,
                "artifact_metadata_path": None,
                "file_size_bytes": None,
                "link_mode": None,
                "metadata_link_mode": None,
            },
            "failure": None,
        }
        self._write_manifest()

    def _write_manifest(self) -> None:
        _write_json(self.manifest_path, self._manifest)

    def record_translation(self, prompt: "ImagePrompt", *, duration_ms: int) -> None:
        self.prompt_path.write_text(prompt.prompt_text.rstrip() + "\n", encoding="utf-8")
        self._manifest["files"]["prompt_path"] = str(self.prompt_path)

        if prompt.translation_request_text:
            self.translation_request_path.write_text(
                prompt.translation_request_text.rstrip() + "\n",
                encoding="utf-8",
            )
            self._manifest["files"]["translation_request_path"] = str(
                self.translation_request_path
            )

        if prompt.model_response_text:
            self.translation_response_path.write_text(
                prompt.model_response_text.rstrip() + "\n",
                encoding="utf-8",
            )
            self._manifest["files"]["translation_response_path"] = str(
                self.translation_response_path
            )

        retry_events = list(prompt.translation_retry_events)
        self._manifest["timings_ms"]["translate"] = duration_ms
        self._manifest["translation"] = {
            "status": "succeeded",
            "mode_requested": self._run_artifacts._config.translation_mode,
            "backend_used": prompt.translation_backend,
            "model": self._run_artifacts._config.gemini_model
            if prompt.translation_backend == "vertex"
            else None,
            "aspect_ratio": prompt.aspect_ratio,
            "prompt_length": len(prompt.prompt_text),
            "used_fallback": prompt.translation_used_fallback,
            "fallback_reason": prompt.translation_fallback_reason,
            "retry_count": len(retry_events),
            "attempt_count": len(retry_events) + 1,
            "retry_events": retry_events,
            "temperature": self._run_artifacts._config.translation_temperature,
            "top_p": self._run_artifacts._config.translation_top_p,
            "seed": self._run_artifacts._config.translation_seed,
        }
        self._write_manifest()

    def record_dry_run(self) -> None:
        self._manifest["paint"]["status"] = "skipped"
        self._write_manifest()

    def record_paint_success(
        self,
        *,
        duration_ms: int,
        image_byte_count: int,
        diagnostics: dict[str, Any],
    ) -> None:
        retry_events = list(diagnostics.get("retry_events", []))
        self._manifest["timings_ms"]["paint"] = duration_ms
        self._manifest["paint"] = {
            "status": "succeeded",
            "model": self._run_artifacts._config.image_model,
            "image_size": self._run_artifacts._config.image_size,
            "candidate_count_requested": self._run_artifacts._config.image_candidate_count,
            "seed": self._run_artifacts._config.image_seed,
            "retry_count": len(retry_events),
            "attempt_count": len(retry_events) + 1,
            "retry_events": retry_events,
            "candidate_image_count": diagnostics.get("candidate_image_count"),
            "selected_candidate_index": diagnostics.get("selected_candidate_index"),
            "selection_method": diagnostics.get("selection_method"),
            "result_bytes": image_byte_count,
        }
        self._write_manifest()

    def record_paint_failure(
        self,
        *,
        exc: BaseException,
        duration_ms: int,
        diagnostics: dict[str, Any],
        failed_prompt_path: Path | None,
    ) -> None:
        retry_events = list(diagnostics.get("retry_events", []))
        self._manifest["timings_ms"]["paint"] = duration_ms
        self._manifest["paint"] = {
            "status": "failed",
            "model": self._run_artifacts._config.image_model,
            "image_size": self._run_artifacts._config.image_size,
            "candidate_count_requested": self._run_artifacts._config.image_candidate_count,
            "seed": self._run_artifacts._config.image_seed,
            "retry_count": len(retry_events),
            "attempt_count": len(retry_events) + 1 if diagnostics else 1,
            "retry_events": retry_events,
            "candidate_image_count": diagnostics.get("candidate_image_count"),
            "selected_candidate_index": diagnostics.get("selected_candidate_index"),
            "selection_method": diagnostics.get("selection_method"),
            "result_bytes": None,
        }
        self._manifest["failure"] = {
            "stage": "paint",
            **_exception_payload(exc),
        }
        if failed_prompt_path is not None:
            self._manifest["files"]["legacy_failed_prompt_path"] = str(
                failed_prompt_path.resolve()
            )
        self.error_path.write_text(_traceback_text(exc), encoding="utf-8")
        self._manifest["files"]["error_path"] = str(self.error_path)
        self._write_manifest()

    def record_unhandled_failure(
        self,
        *,
        stage: str,
        exc: BaseException,
    ) -> None:
        self._manifest["failure"] = {
            "stage": stage,
            **_exception_payload(exc),
        }
        self.error_path.write_text(_traceback_text(exc), encoding="utf-8")
        self._manifest["files"]["error_path"] = str(self.error_path)
        self._write_manifest()

    def record_storage(
        self,
        *,
        primary_path: Path,
        duration_ms: int,
    ) -> None:
        self._manifest["timings_ms"]["store"] = duration_ms

        artifact_result_path = self.block_dir / f"result{primary_path.suffix}"
        link_mode = _link_or_copy(primary_path, artifact_result_path)

        primary_metadata_path = primary_path.with_suffix(".metadata.json")
        artifact_metadata_path: Path | None = None
        metadata_link_mode: str | None = None
        if primary_metadata_path.exists():
            artifact_metadata_path = artifact_result_path.with_suffix(".metadata.json")
            metadata_link_mode = _link_or_copy(
                primary_metadata_path,
                artifact_metadata_path,
            )

        self.result_path = artifact_result_path
        self.result_metadata_path = artifact_metadata_path

        file_size = primary_path.stat().st_size
        self._manifest["output"] = {
            "format": primary_path.suffix.lstrip("."),
            "primary_path": str(primary_path.resolve()),
            "artifact_result_path": str(artifact_result_path.resolve()),
            "primary_metadata_path": (
                str(primary_metadata_path.resolve()) if primary_metadata_path.exists() else None
            ),
            "artifact_metadata_path": (
                str(artifact_metadata_path.resolve())
                if artifact_metadata_path is not None
                else None
            ),
            "file_size_bytes": file_size,
            "link_mode": link_mode,
            "metadata_link_mode": metadata_link_mode,
        }
        self._manifest["files"]["result_path"] = str(artifact_result_path)
        self._manifest["files"]["result_metadata_path"] = (
            str(artifact_metadata_path) if artifact_metadata_path is not None else None
        )
        self._write_manifest()

    def finalize(self, *, status: str, total_duration_ms: int) -> None:
        self._manifest["status"] = status
        self._manifest["completed_at"] = _utc_now().isoformat()
        self._manifest["timings_ms"]["total"] = total_duration_ms
        self._write_manifest()

        summary = {
            "block_index": self._block.index,
            "status": status,
            "line_number": self._block.line_number,
            "diagram_type": self._block.diagram_type,
            "manifest_path": str(self.manifest_path),
            "artifact_dir": str(self.block_dir),
            "output_path": self._manifest["output"]["primary_path"],
        }
        self._run_artifacts.register_block(summary)
