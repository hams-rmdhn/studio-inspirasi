# SPDX-License-Identifier: AGPL-3.0-or-later
import unittest

from ci_timings import elapsed, summarise


class TimingReportTests(unittest.TestCase):
    def report(self, jobs):
        return summarise({"jobs": jobs}, source="a" * 40, run_id=123,
                         repository="tulcoturo/clovercut", cache_state="unknown",
                         runner_label=None)

    def test_skipped_and_incomplete_steps_are_unavailable(self):
        steps = [
            {"name": "Build the tests", "status": "completed", "conclusion": "skipped",
             "startedAt": "2026-10-28T10:00:00Z", "completedAt": "2026-10-28T10:01:00Z"},
            {"name": "Run the tests", "status": "in_progress", "conclusion": "",
             "startedAt": "2026-10-28T10:01:00Z", "completedAt": "0001-01-01T00:00:00Z"},
        ]
        job = self.report([{"name": "Engine", "status": "in_progress", "steps": steps}])["jobs"][0]
        self.assertIsNone(job["wall_seconds"])
        self.assertEqual([step["seconds"] for step in job["steps"]], [None, None])
        self.assertEqual(job["observed_step_seconds_by_category"], {})

    def test_rest_and_cli_shapes_preserve_failed_work_and_build_cost(self):
        for start, end in [("started_at", "completed_at"), ("startedAt", "completedAt")]:
            with self.subTest(shape=start):
                job = {"name": "Engine", "status": "completed", "conclusion": "failure",
                       start: "2026-10-28T10:00:00Z", end: "2026-10-28T10:02:00Z",
                       "steps": [{"name": "Run the gRPC tests", "status": "completed",
                                  "conclusion": "failure", start: "2026-10-28T10:00:05Z",
                                  end: "2026-10-28T10:01:45Z"}]}
                report = self.report([job])
                self.assertEqual(report["cache_state"], "unknown")
                measured = report["jobs"][0]
                self.assertEqual(measured["wall_seconds"], 120)
                self.assertEqual(measured["observed_step_seconds_by_category"],
                                 {"grpc_build_and_execution": 100})
                self.assertEqual(measured["steps"][0]["conclusion"], "failure")

    def test_missing_zero_duration_and_timezone_intervals_remain_distinct(self):
        self.assertIsNone(elapsed(None, None))
        self.assertIsNone(elapsed("0001-01-01T00:00:00Z", "0001-01-01T00:00:00Z"))
        self.assertEqual(elapsed("2026-10-28T10:00:00Z", "2026-10-28T11:00:00+01:00"), 0)
        with self.assertRaises(ValueError):
            elapsed("2026-10-28T10:00:01Z", "2026-10-28T10:00:00Z")
        with self.assertRaises(ValueError):
            elapsed("2026-10-28T10:00:00", "2026-10-28T10:00:01")

    def test_rejects_abbreviated_source(self):
        with self.assertRaisesRegex(ValueError, "full tested commit"):
            summarise({"jobs": []}, source="abcd1234", run_id=123,
                      repository="tulcoturo/clovercut", cache_state="unknown", runner_label=None)


if __name__ == "__main__":
    unittest.main()
