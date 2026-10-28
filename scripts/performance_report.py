#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Collect phase-6 JSON records; partial execution is never a passing benchmark."""
import argparse
import json
import math
from pathlib import Path
import re

PREFIX = "CLOVERCUT_BENCHMARK "
EVENTS = {"context", "samples", "memory", "lifecycle", "complete"}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def collect(log, *, exit_code=None):
    records = []
    context = None
    complete = False
    for line in log.splitlines():
        if PREFIX not in line:
            continue
        if complete:
            raise ValueError("records follow the completion marker; select a single probe log")
        record = json.loads(line.partition(PREFIX)[2])
        if record.get("schema_version") != 1 or record.get("event") not in EVENTS:
            raise ValueError("unsupported benchmark record")
        event, data = record["event"], record.get("data")
        if not isinstance(data, dict):
            raise ValueError("record data must be an object")
        if event == "context":
            if context is not None:
                raise ValueError("multiple probe contexts; select a single run")
            context = data
            source = context.get("source_sha")
            if source is not None and not re.fullmatch(r"[0-9a-f]{40}", source):
                raise ValueError("source_sha must be a full commit SHA or null")
        elif event == "samples":
            values = data.get("values")
            if (data.get("unit") != "ms" or not isinstance(values, list) or not values
                    or not all(number(value) for value in values)
                    or not all(number(data.get(key)) for key in ("mean", "p95", "max"))):
                raise ValueError("sample timings must be nonempty, finite and nonnegative")
        elif event == "memory":
            if not all(data.get(key) is None or number(data[key])
                       for key in ("rss_bytes", "high_water_bytes")):
                raise ValueError("memory counters must be nonnegative or null")
        elif event == "complete":
            if data.get("lifecycle_assertions") != "passed":
                raise ValueError("completion does not confirm lifecycle assertions")
            complete = True
        records.append(record)
    if not records:
        raise ValueError("no benchmark records; the selected test may not have executed")
    if complete and (context is None or not {"samples", "memory", "lifecycle"}.issubset(
            {record["event"] for record in records})):
        raise ValueError("completion marker without required benchmark records")
    return {"schema_version": 1, "status": "complete" if complete and exit_code == 0 else "incomplete",
            "records_complete": complete, "process_exit_code": exit_code,
            "metadata_complete": bool(context and all(context.get(key) for key in
                ("source_sha", "machine_label", "toolchain", "os", "architecture"))),
            "performance_budget_qualified": False, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True, help="exit status of the cargo/test command")
    args = parser.parse_args()
    try:
        report = collect(args.log.read_text(), exit_code=args.exit_code)
    except (ValueError, TypeError, AttributeError) as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if report["status"] != "complete":
        parser.exit(1, "Incomplete/failed probe: records retained; no passing qualification.\n")


if __name__ == "__main__":
    main()
