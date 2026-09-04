from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")


@dataclass(frozen=True)
class VerificationHandoff:
    schema_version: str
    provider: str
    required_check: str
    project_id: str
    task_id: str
    attempt_id: int
    lease_epoch: int
    branch: str
    base_sha: str
    commit_sha: str
    diff_sha256: str
    acceptance_contract: Mapping[str, Any]

    def as_machine_input(self) -> str:
        payload = asdict(self)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_verification_handoff(
    *,
    project_id: str,
    task_id: str,
    attempt_id: int,
    lease_epoch: int,
    branch: str,
    base_sha: str,
    commit_sha: str,
    diff_bytes: bytes,
    acceptance_contract: Mapping[str, Any],
) -> VerificationHandoff:
    if not project_id or not task_id or not branch:
        raise ValueError("project_id, task_id, and branch are required")
    if not SHA_RE.fullmatch(base_sha) or not SHA_RE.fullmatch(commit_sha):
        raise ValueError("base_sha and commit_sha must be hexadecimal Git object IDs")
    if attempt_id < 1 or lease_epoch < 1:
        raise ValueError("attempt_id and lease_epoch must be positive")
    if not isinstance(acceptance_contract, Mapping) or not acceptance_contract:
        raise ValueError("acceptance_contract must be a non-empty machine mapping")
    return VerificationHandoff(
        schema_version="phase1.verification.v1",
        provider="github-hosted",
        required_check="authoritative-ci",
        project_id=project_id,
        task_id=task_id,
        attempt_id=attempt_id,
        lease_epoch=lease_epoch,
        branch=branch,
        base_sha=base_sha,
        commit_sha=commit_sha,
        diff_sha256=hashlib.sha256(diff_bytes).hexdigest(),
        acceptance_contract=dict(acceptance_contract),
    )
