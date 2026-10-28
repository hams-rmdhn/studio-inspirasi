#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Summarise GitHub job timings without treating unknown cache state as cold/warm.

Input: gh run view RUN --json jobs, or the REST jobs endpoint (all pages merged).
No network access, credentials, log scraping or inferred performance budgets.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re


def elapsed(start, end):
    """Missing timestamps are unavailable, never zero or time since the epoch."""
    if not start or not end or start.startswith("0001-") or end.startswith("0001-"):
        return None
    begin = datetime.fromisoformat(start.replace("Z", "+00:00"))
    finish = datetime.fromisoformat(end.replace("Z", "+00:00"))
    if begin.utcoffset() is None or finish.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    seconds = (finish - begin).total_seconds()
    if seconds < 0:
        raise ValueError("a completed interval ends before it starts")
    return seconds


def category(name):
    if name == "Build the tests":
        return "test_build"
    if name == "Run the tests":
        return "test_execution"
    if name == "Run the gRPC tests":
        return "grpc_build_and_execution"
    if name == "Run the documentation's examples":
        return "documentation_build_and_execution"
    if "cargo clippy" in name:
        return "grpc_lint" if "--features grpc" in name else "workspace_lint"
    if name in ("System libraries", "FFmpeg development libraries", "ONNX Runtime",
                "sherpa-onnx libraries", "Prebuilt native libraries", "Native libraries"):
        return "native_dependencies"
    return "other"


def summarise(payload, *, source, run_id, repository, cache_state, runner_label):
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("source must be the full tested commit SHA, not a workflow branch")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("invalid repository")
    if run_id <= 0:
        raise ValueError("run ID must be positive")
    if cache_state not in ("unknown", "cold", "warm"):
        raise ValueError("invalid cache state")
    jobs = payload["jobs"]
    result = []
    for job in jobs:
        steps = []
        totals = {}
        for step in job.get("steps", []):
            seconds = elapsed(
                step.get("startedAt", step.get("started_at")),
                step.get("completedAt", step.get("completed_at")),
            ) if step.get("status") == "completed" and step.get("conclusion") != "skipped" else None
            group = category(step["name"])
            steps.append({"name": step["name"], "category": group,
                          "status": step.get("status"), "conclusion": step.get("conclusion"),
                          "seconds": seconds})
            if seconds is not None:
                totals[group] = totals.get(group, 0) + seconds
        result.append({
            "name": job["name"], "status": job.get("status"),
            "conclusion": job.get("conclusion"),
            "wall_seconds": elapsed(job.get("startedAt", job.get("started_at")),
                                    job.get("completedAt", job.get("completed_at")))
            if job.get("status") == "completed" and job.get("conclusion") != "skipped" else None,
            "observed_step_seconds_by_category": totals, "steps": steps,
        })
    return {"schema_version": 1, "source_sha": source,
            "run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
            "cache_state": cache_state, "runner_label": runner_label,
            "limitations": [
                "Step wall time includes command overhead; it is not CPU time.",
                "Build-and-execution steps do not separate compilation from test runtime.",
                "Jobs can overlap; their durations are not total workflow wall time.",
                "Compare only equivalent runner, toolchain, profile, dependencies and cache conditions.",
                "Skipped, incomplete and missing intervals are null, not zero.",
            ], "jobs": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True, help="full SHA of the source actually tested")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--repository", default="tulcoturo/clovercut")
    parser.add_argument("--cache-state", choices=("unknown", "cold", "warm"), default="unknown")
    parser.add_argument("--runner-label", default=None, help="documented runner; omit if unknown")
    args = parser.parse_args()
    try:
        report = summarise(json.loads(args.input.read_text()), source=args.source,
                           run_id=args.run_id, repository=args.repository,
                           cache_state=args.cache_state, runner_label=args.runner_label)
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
