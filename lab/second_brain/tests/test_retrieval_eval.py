from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from lab.second_brain.src.retrieval_eval import DEFAULT_BENCHMARK, run_benchmark
from lab.second_brain.src.validate import REPO_ROOT, ValidationFailure


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_public_benchmark_replays_cleanly_without_authority_mutation(self) -> None:
        work = REPO_ROOT / "work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            output = Path(temporary) / "retrieval-report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lab.second_brain.src.retrieval_eval",
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report, json.loads(output.read_text(encoding="utf-8")))
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["authority_unchanged"])
        self.assertEqual(report["summary"]["cases"], 15)
        self.assertEqual(report["summary"]["cases_passed"], 15)
        self.assertEqual(report["summary"]["required_recall"], 1.0)
        self.assertEqual(report["summary"]["forbidden_clean_rate"], 1.0)
        self.assertEqual(report["summary"]["deterministic_cases"], 15)

    def test_unknown_or_contradictory_labels_fail_before_evaluation(self) -> None:
        source = yaml.safe_load((REPO_ROOT / DEFAULT_BENCHMARK).read_text())
        work = REPO_ROOT / "work"
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            path = Path(temporary) / "benchmark.yaml"
            unknown = copy.deepcopy(source)
            unknown["cases"][0]["expected_concepts"][0] = "c_missing_concept"
            path.write_text(yaml.safe_dump(unknown, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "unknown concepts"):
                run_benchmark(path)

            overlap = copy.deepcopy(source)
            concept_id = overlap["cases"][0]["expected_concepts"][0]
            overlap["cases"][0]["forbidden_concepts"][0] = concept_id
            path.write_text(yaml.safe_dump(overlap, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValidationFailure, "expects and forbids"):
                run_benchmark(path)


if __name__ == "__main__":
    unittest.main()
