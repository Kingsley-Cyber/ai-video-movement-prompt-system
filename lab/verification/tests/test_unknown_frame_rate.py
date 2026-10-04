import unittest

from lab.verification.verify import _artifact_checks


class UnknownFrameRateTests(unittest.TestCase):
    def check(self, expected, observed):
        return _artifact_checks(
            {"provider_artifact_checks": [{"check_id": "frame_rate", "comparator": "equals",
                                           "expected": expected, "tolerance": None}]},
            {"sha256": "sha256:" + "a" * 64},
            {"duration_s": 1, "width": 16, "height": 16,
             "frame_rate": observed, "probe_hash": "sha256:" + "b" * 64},
        )[0]

    def test_unknown_does_not_equal_unknown(self):
        row = self.check(None, None)
        self.assertEqual(row["status"], "unobservable")
        self.assertEqual(row["deviation"]["code"], "frame_rate_unknown")

    def test_one_unknown_stays_unobservable(self):
        self.assertEqual(self.check(None, 24)["status"], "unobservable")
        self.assertEqual(self.check(24, None)["status"], "unobservable")

    def test_known_frame_rates_still_compare(self):
        self.assertEqual(self.check(24, 24)["status"], "pass")
        self.assertEqual(self.check(24, 30)["status"], "fail")
