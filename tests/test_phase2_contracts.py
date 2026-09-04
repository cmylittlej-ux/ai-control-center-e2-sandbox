from __future__ import annotations

import unittest
from pathlib import Path

from control_kernel.errors import UnsupportedRuntime
from control_kernel.phase2 import (
    CI_FAILURE_CLASSES,
    IndependentReviewer,
    MAX_WORKERS,
    WORKER_SLOTS,
    classify_ci_failure,
    detect_base_drift,
    deterministic_branch,
    deterministic_runtime_dir,
    deterministic_worktree,
    detect_hotspot_conflict,
    ReviewerProtocolError,
)


class Phase2ContractTests(unittest.TestCase):
    def test_exactly_two_fixed_worker_slots_and_no_scaling(self) -> None:
        self.assertEqual(WORKER_SLOTS, ("worker_slot_1", "worker_slot_2"))
        self.assertEqual(MAX_WORKERS, 2)

    def test_deterministic_branch_worktree_and_runtime_names(self) -> None:
        self.assertEqual(deterministic_branch("task-a", 2), "task/task-a/attempt-2")
        self.assertEqual(
            deterministic_worktree(Path("/tmp/worktrees"), "worker_slot_1", "task-a", 2).as_posix(),
            str(Path("/tmp/worktrees/worker_slot_1/task-a/attempt-2").resolve()),
        )
        self.assertEqual(
            deterministic_runtime_dir(Path("/tmp/runtime"), "worker_slot_2", "task-b", 1).as_posix(),
            str(Path("/tmp/runtime/worker_slot_2/task-b/attempt-1").resolve()),
        )

    def test_ci_failure_classification_is_deterministic_and_bounded(self) -> None:
        self.assertIsNone(classify_ci_failure(conclusion="success"))
        self.assertEqual(classify_ci_failure(conclusion="failure", job_name="lint"), "LINT_FAILURE")
        self.assertEqual(classify_ci_failure(conclusion="failure", output="runner network unavailable"), "INFRA_FAILURE")
        self.assertEqual(classify_ci_failure(conclusion="failure", output="ordinary assertion failed"), "TEST_FAILURE")
        self.assertEqual(
            set(CI_FAILURE_CLASSES),
            {"TEST_FAILURE", "BUILD_FAILURE", "LINT_FAILURE", "POLICY_FAILURE", "INFRA_FAILURE", "TIMEOUT", "CANCELLED"},
        )

    def test_base_drift_records_old_and_current_sha(self) -> None:
        self.assertEqual(
            detect_base_drift(expected_base_sha="a" * 40, current_base_sha="a" * 40),
            {"drifted": False, "old_base_sha": "a" * 40, "current_base_sha": "a" * 40, "action": "CONTINUE", "reason_code": None},
        )
        drift = detect_base_drift(expected_base_sha="a" * 40, current_base_sha="b" * 40)
        self.assertTrue(drift["drifted"])
        self.assertEqual(drift["reason_code"], "BASE_DRIFT")
        self.assertEqual(drift["action"], "REVERIFY_OR_REBASE")

    def test_hotspot_conflict_uses_explicit_paths_only(self) -> None:
        self.assertEqual(
            detect_hotspot_conflict(left_paths=["src/a.py", "README.md"], right_paths=["src/b.py"]),
            {"conflict": False, "hotspot_paths": [], "reason_code": None, "action": "CONTINUE"},
        )
        conflict = detect_hotspot_conflict(left_paths=["./src/a.py"], right_paths=["src/a.py", "src/b.py"])
        self.assertEqual(conflict["hotspot_paths"], ["src/a.py"])
        self.assertEqual(conflict["reason_code"], "GIT_CONFLICT")

    def test_reviewer_requires_fresh_independent_context_and_structured_decision(self) -> None:
        reviewer = IndependentReviewer(reviewer_id="sol-reviewer", reviewer_model="Sol")
        evidence = {"authoritative_ci_conclusion": "success", "run_id": "123"}
        first = reviewer.review(
            worker_id="worker-a",
            machine_evidence=evidence,
            frozen_acceptance={"checks": ["authoritative-ci"]},
            diff_bytes=b"diff",
            forced_decision="REJECT",
        )
        second = reviewer.review(
            worker_id="worker-b",
            machine_evidence=evidence,
            frozen_acceptance={"checks": ["authoritative-ci"]},
            diff_bytes=b"diff",
            forced_decision="ACCEPT",
        )
        self.assertEqual(first.decision, "REJECT")
        self.assertEqual(second.decision, "ACCEPT")
        self.assertNotEqual(first.reviewer_context_id, second.reviewer_context_id)
        self.assertNotEqual(first.input_digest, "")

    def test_reviewer_rejects_self_assessment_self_review_and_unapproved_substitute(self) -> None:
        reviewer = IndependentReviewer(reviewer_id="worker-a", reviewer_model="Sol")
        with self.assertRaises(ReviewerProtocolError):
            reviewer.review(
                worker_id="worker-a",
                machine_evidence={"ok": True},
                frozen_acceptance={"checks": ["ci"]},
                diff_bytes=b"diff",
            )
        reviewer = IndependentReviewer(reviewer_id="sol-reviewer", reviewer_model="Other")
        with self.assertRaises(UnsupportedRuntime):
            reviewer.review(
                worker_id="worker-a",
                machine_evidence={"ok": True},
                frozen_acceptance={"checks": ["ci"]},
                diff_bytes=b"diff",
            )
        reviewer = IndependentReviewer()
        with self.assertRaises(ReviewerProtocolError):
            reviewer.review(
                worker_id="worker-a",
                machine_evidence={"worker_self_assessment": "done"},
                frozen_acceptance={"checks": ["ci"]},
                diff_bytes=b"diff",
            )
if __name__ == "__main__":
    unittest.main()
