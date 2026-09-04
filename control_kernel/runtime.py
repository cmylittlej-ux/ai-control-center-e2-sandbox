from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .errors import UnsupportedRuntime


EXPECTED_CODEX_VERSION = "0.153.2"
SCHEMA_GENERATION_COMMAND = ("codex", "app-server", "generate-json-schema", "--experimental", "--out")


@dataclass(frozen=True)
class RuntimePin:
    codex_cli_version: str
    executable_path: Path
    executable_sha256: str
    schema_path: Path
    schema_sha256: str
    fail_closed: bool = True

    @classmethod
    def from_json(cls, path: Path) -> "RuntimePin":
        data = json.loads(path.read_text(encoding="utf-8"))
        version = data.get("codex_cli_version")
        executable_path = data.get("executable_path")
        executable_sha256 = data.get("executable_sha256")
        schema_path = data.get("schema_path")
        schema_sha256 = data.get("schema_sha256")
        if (
            not isinstance(version, str)
            or not isinstance(executable_path, str)
            or not isinstance(executable_sha256, str)
            or not isinstance(schema_path, str)
            or not isinstance(schema_sha256, str)
        ):
            raise UnsupportedRuntime("runtime pin is incomplete; refusing to start")
        return cls(
            version,
            Path(executable_path),
            executable_sha256,
            _resolve_pin_path(path, schema_path),
            schema_sha256,
            bool(data.get("fail_closed", True)),
        )

    def validate(self, reported_version: str, executable_path: Path | None = None) -> None:
        if reported_version != self.codex_cli_version:
            raise UnsupportedRuntime(f"Codex version {reported_version!r} does not match pin {self.codex_cli_version!r}")
        if not self.fail_closed:
            raise UnsupportedRuntime("runtime pin must fail closed")
        executable = executable_path or self.executable_path
        if not executable.is_file():
            raise UnsupportedRuntime(f"pinned Codex executable is missing: {executable}")
        executable_observed = hashlib.sha256(executable.read_bytes()).hexdigest()
        if executable_observed != self.executable_sha256:
            raise UnsupportedRuntime("pinned Codex executable digest mismatch")
        if not self.schema_path.is_file():
            raise UnsupportedRuntime(f"pinned App Server schema is missing: {self.schema_path}")
        observed = hashlib.sha256(self.schema_path.read_bytes()).hexdigest()
        if observed != self.schema_sha256:
            raise UnsupportedRuntime("pinned App Server schema digest mismatch")


def _resolve_pin_path(pin_file: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    relative_to_pin = (pin_file.parent / candidate).resolve(strict=False)
    if relative_to_pin.is_file():
        return relative_to_pin
    return (pin_file.parent.parent / candidate).resolve(strict=False)


def validate_runtime(
    reported_version: str,
    schema_bytes: bytes,
    expected_version: str = EXPECTED_CODEX_VERSION,
    expected_schema_sha256: str | None = None,
) -> str:
    if reported_version != expected_version:
        raise UnsupportedRuntime(f"Codex version {reported_version!r} does not match pin {expected_version!r}")
    if not expected_schema_sha256:
        raise UnsupportedRuntime("exact version-specific App Server schema digest is not pinned")
    observed = hashlib.sha256(schema_bytes).hexdigest()
    if observed != expected_schema_sha256:
        raise UnsupportedRuntime("App Server schema digest does not match the pinned artifact")
    return observed
