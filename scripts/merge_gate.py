# SPDX-License-Identifier: Apache-2.0
"""Merge gate evaluator — checks that all required jobs passed.

Used by the pr-compliance reusable workflow to aggregate job results
and block merge if any required job failed.

Usage:
    python merge_gate.py '{"job1": "success", "job2": "skipped", "job3": "success"}'

Exit code 0 if all jobs succeeded or were skipped, 1 otherwise.
"""

import json
import sys


def evaluate(results: dict[str, str]) -> bool:
    """Return True if all jobs passed (success or skipped)."""
    for job, result in results.items():
        if result not in ("success", "skipped"):
            print(f"FAIL: {job} = {result}")
            return False
        print(f"OK:   {job} = {result}")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} '<json-results>'")
        sys.exit(2)
    results = json.loads(sys.argv[1])
    sys.exit(0 if evaluate(results) else 1)
