# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import unittest
from performance_report import PREFIX, collect


def line(event, data):
    return PREFIX + json.dumps({"schema_version": 1, "event": event, "data": data}) + "\n"


class PerformanceReportTests(unittest.TestCase):
    def fixture(self):
        return ("running 1 test\ntest probe ... " + line("context", {
            "source_sha": "a" * 40, "machine_label": "reference", "toolchain": "rustc 1.93.1",
            "os": "linux", "architecture": "x86_64"})
            + line("samples", {"unit": "ms", "values": [1, 2, 30], "mean": 11, "p95": 30, "max": 30})
            + line("memory", {"rss_bytes": None, "high_water_bytes": 0, "drm_device_wide_vram_bytes": [["card7", 0]]})
            + line("lifecycle", {"cpu_pool_bytes": [100, 0]}))

    def test_partial_run_is_not_a_pass_and_retains_raw_measurements(self):
        report = collect(self.fixture())
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["records"][1]["data"]["values"], [1, 2, 30])
        self.assertIsNone(report["records"][2]["data"]["rss_bytes"])
        self.assertEqual(report["records"][2]["data"]["high_water_bytes"], 0)

    def test_completed_run_does_not_qualify_a_performance_budget(self):
        log = self.fixture() + line("complete", {"lifecycle_assertions": "passed"})
        report = collect(log, exit_code=0)
        self.assertEqual(report["status"], "complete")
        self.assertTrue(report["metadata_complete"])
        self.assertFalse(report["performance_budget_qualified"])
        for exit_code in (None, 1, 134):
            failed = collect(log, exit_code=exit_code)
            self.assertEqual(failed["status"], "incomplete")
            self.assertTrue(failed["records_complete"])
        self.assertFalse(collect(line("context", {}))["metadata_complete"])

    def test_no_test_execution_unknown_schema_and_duplicate_runs_are_rejected(self):
        for log in ["running 0 tests\n", PREFIX + '{"schema_version": 2}\n',
                    self.fixture() * 2,
                    self.fixture() + line("complete", {"lifecycle_assertions": "passed"}) + self.fixture(),
                    line("complete", {"lifecycle_assertions": "passed"})]:
            with self.subTest(log=log[:50]), self.assertRaises(ValueError):
                collect(log)

    def test_nonfinite_negative_and_empty_timings_are_rejected(self):
        for values in [[float("nan")], [float("inf")], [-1], [], [True]]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                collect(line("samples", {"unit": "ms", "values": values, "mean": 0, "p95": 0, "max": 0}))


if __name__ == "__main__":
    unittest.main()
