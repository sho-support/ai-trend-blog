#!/usr/bin/env python3
"""Billing regressions: use real fallback functions with a stub API, no spend."""
import ast
import contextlib
import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gemini_budget_guard import billing_block_reason, stop_if_monthly_cap_exceeded
import run_generate_with_retry as retry

DEPLETED = "402 RESOURCE_EXHAUSTED. Your prepayment credits are depleted."


class BillingTests(unittest.TestCase):
    def test_billing_errors_are_not_transient(self):
        for message in (DEPLETED, "429 RESOURCE_EXHAUSTED monthly spending cap",
                        "Monthly spend cap reached", "[gemini-billing-blocked]"):
            with self.subTest(message=message):
                self.assertFalse(retry.is_transient_error(message))
        for message in ("503 UNAVAILABLE", "429 RESOURCE_EXHAUSTED rate limit",
                        "read timed out"):
            with self.subTest(message=message):
                self.assertTrue(retry.is_transient_error(message))
                self.assertIsNone(billing_block_reason(message))

    def test_every_generator_stops_before_model_fallback(self):
        files = ("generate_article.py", "generate_note_draft.py",
                 "collect_paid_info_candidates.py", "verify_paid_info_candidates.py",
                 "generate_paid_note_draft.py", "review_note_drafts.py")
        for filename in files:
            with self.subTest(filename=filename):
                tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
                function = next(node for node in tree.body
                                if isinstance(node, ast.FunctionDef)
                                and node.name == "generate_content_with_fallback")
                generate = Mock(side_effect=RuntimeError(DEPLETED))
                sleep = Mock(side_effect=AssertionError("must not wait on billing"))
                namespace = {
                    "MODEL_NAME": "test-primary", "FALLBACK_MODEL_NAMES": ["test-fallback"],
                    "client": SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
                    "time": SimpleNamespace(sleep=sleep),
                    "stop_if_monthly_cap_exceeded": stop_if_monthly_cap_exceeded,
                }
                exec(compile(ast.Module(body=[function], type_ignores=[]), filename, "exec"), namespace)
                output = io.StringIO()
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as error:
                    namespace[function.name]("test", "test")
                self.assertEqual(error.exception.code, 1)
                self.assertEqual(generate.call_count, 1)
                sleep.assert_not_called()
                self.assertIn("[gemini-billing-blocked]", output.getvalue())

    def test_outer_retry_does_not_repeat_billing_failure(self):
        for message in (DEPLETED, "[gemini-billing-blocked] 前払い残高切れ"):
            result = SimpleNamespace(returncode=1, stdout=message, stderr="")
            with self.subTest(message=message), patch.object(retry.subprocess, "run", return_value=result) as run, \
                    patch.object(retry.time, "sleep") as sleep, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(retry.main(), 1)
                self.assertEqual(run.call_count, 1)
                sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
