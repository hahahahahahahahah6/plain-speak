"""Smoke tests for plain-speak (stdlib only, unittest).

Run:  python3 -m unittest tests.test_smoke -v
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import plain_speak  # noqa: E402

SLOP_TEXT = (
    "In today's fast-paced digital landscape, it is crucial to leverage "
    "cutting-edge tools in order to unlock the potential of your workflow "
    "and foster a seamless experience that is robust, comprehensive, and "
    "holistic across every paradigm.\n"
    "Furthermore, one might argue that to truly elevate your productivity, "
    "you must delve into the intricate tapestry of modern software "
    "development and meticulously navigate its ever-evolving synergy, "
    "which is arguably a testament to the dynamic nature of this vibrant "
    "realm.\n"
    "Perhaps it is generally somewhat difficult to underscore the pivotal "
    "role of empowerment, but deep dives are nonetheless noteworthy.\n"
)

PLAIN_TEXT = (
    "Cats sleep most of the day.\n"
    "A cat needs about sixteen hours of sleep.\n"
    "Kittens play hard and nap after.\n"
    "Give your cat fresh water every day.\n"
)


def run_cli(argv, stdin_text=None):
    """Run main() capturing stdout; return (exit_code, stdout)."""
    old_stdin = sys.stdin
    buf = io.StringIO()
    try:
        if stdin_text is not None:
            sys.stdin = io.StringIO(stdin_text)
        with contextlib.redirect_stdout(buf):
            code = plain_speak.main(argv)
    finally:
        sys.stdin = old_stdin
    return code, buf.getvalue()


class TestScoring(unittest.TestCase):
    def test_slop_text_scores_low(self):
        result = plain_speak.analyze(SLOP_TEXT)
        self.assertLess(result["plainness"], 60, result)
        self.assertEqual(result["grade"], "slop")
        self.assertGreater(result["stats"]["long_sentences"], 0)
        self.assertGreater(result["stats"]["buzzword_hits"], 0)
        self.assertGreater(result["stats"]["hedge_hits"], 0)
        self.assertLess(result["stats"]["reading_ease"], 60)

    def test_plain_text_scores_high(self):
        result = plain_speak.analyze(PLAIN_TEXT)
        self.assertGreaterEqual(result["plainness"], 90, result)
        self.assertEqual(result["grade"], "plain")
        self.assertEqual(result["stats"]["long_sentences"], 0)
        self.assertEqual(result["stats"]["buzzword_hits"], 0)
        self.assertEqual(result["findings"], [])

    def test_empty_input_is_plain(self):
        result = plain_speak.analyze("")
        self.assertEqual(result["plainness"], 100)
        self.assertEqual(result["stats"]["reading_ease"], 100.0)

    def test_findings_carry_rule_ids_and_lines(self):
        result = plain_speak.analyze(SLOP_TEXT)
        rules = {f["rule"] for f in result["findings"]}
        self.assertTrue({"long-sentence", "buzzword", "hedge"} <= rules)
        lines = {f["line"] for f in result["findings"]}
        self.assertEqual(lines, {1, 2, 3})
        # Buzzword findings report the offending word.
        buzz = [f for f in result["findings"] if f["rule"] == "buzzword"]
        joined = " ".join(f["message"] for f in buzz).lower()
        self.assertIn("leverage", joined)
        self.assertIn("tapestry", joined)


class TestCLI(unittest.TestCase):
    def test_check_file(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(SLOP_TEXT)
            path = fh.name
        try:
            code, out = run_cli(["check", path])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        self.assertIn("plainness:", out)
        self.assertIn("buzzword", out)

    def test_stdin_works(self):
        code, out = run_cli(["check"], stdin_text=PLAIN_TEXT)
        self.assertEqual(code, 0)
        self.assertIn("plainness: 100/100 (plain)", out)
        self.assertIn("No findings", out)

    def test_json_output_valid(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(SLOP_TEXT)
            path = fh.name
        try:
            code, out = run_cli(["check", path, "--json"])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("plainness", data)
        self.assertIn("findings", data)
        self.assertIsInstance(data["findings"], list)
        self.assertIn("stats", data)

    def test_fail_under_exits_1_on_slop(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(SLOP_TEXT)
            path = fh.name
        try:
            code, _ = run_cli(["check", path, "--fail-under", "80"])
        finally:
            os.unlink(path)
        self.assertEqual(code, 1)

    def test_fail_under_exits_0_on_plain(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8") as fh:
            fh.write(PLAIN_TEXT)
            path = fh.name
        try:
            code, _ = run_cli(["check", path, "--fail-under", "80"])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)

    def test_missing_file_errors(self):
        with self.assertRaises((FileNotFoundError, OSError)):
            run_cli(["check", "/nonexistent/path/plain-speak-test.txt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
