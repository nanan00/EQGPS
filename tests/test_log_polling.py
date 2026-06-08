import unittest

from eqgps.log_polling import read_then_prune_safely
from eqgps.log_prune import LogPruneResult


class LogPollingTests(unittest.TestCase):
    def test_read_failure_is_reported_without_retrying_the_tailer(self):
        read_attempts = 0

        def read_log():
            nonlocal read_attempts
            read_attempts += 1
            raise OSError("log locked")

        def prune_log():
            self.fail("prune should not run when reading failed")

        outcome = read_then_prune_safely(read_log, prune_log)

        self.assertEqual(read_attempts, 1)
        self.assertIsNotNone(outcome.read_error)
        self.assertIsNone(outcome.prune_error)
        self.assertIsNone(outcome.prune_result)
        self.assertEqual(outcome.status_text("poll"), "Log poll skipped: log locked")

    def test_prune_failure_is_reported_without_retrying_the_successful_read(self):
        read_attempts = 0
        prune_attempts = 0

        def read_log():
            nonlocal read_attempts
            read_attempts += 1

        def prune_log():
            nonlocal prune_attempts
            prune_attempts += 1
            raise OSError("archive denied")

        outcome = read_then_prune_safely(read_log, prune_log)

        self.assertEqual(read_attempts, 1)
        self.assertEqual(prune_attempts, 1)
        self.assertIsNone(outcome.read_error)
        self.assertIsNotNone(outcome.prune_error)
        self.assertIsNone(outcome.prune_result)
        self.assertEqual(outcome.status_text("poll"), "Log prune skipped: archive denied")

    def test_success_returns_prune_result(self):
        expected = LogPruneResult(pruned=False)

        outcome = read_then_prune_safely(lambda: None, lambda: expected)

        self.assertIsNone(outcome.read_error)
        self.assertIsNone(outcome.prune_error)
        self.assertIs(outcome.prune_result, expected)
        self.assertIsNone(outcome.status_text("poll"))


if __name__ == "__main__":
    unittest.main()
