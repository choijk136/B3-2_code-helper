import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.content


class GeneratorTests(unittest.TestCase):
    def test_render_rules(self):
        output = main.render("commit", {"title": "a" * 90, "body": ["- main.py 변경"]})
        self.assertEqual(len(output.splitlines()[1]), 72)
        self.assertIn("- main.py 변경", output)
        pr = main.render("pr", {"title": "x" * 90, "why": ["이유"], "what": ["내용"], "how_to_test": ["명령 실행"]})
        self.assertEqual(len(pr.splitlines()[1]), 80)
        for section in ("Why", "What", "How to Test"):
            self.assertIn("## " + section + "\n- ", pr)
        with self.assertRaises(main.ToolError):
            main.render("pr", {"title": "제목", "why": [], "what": ["x"], "how_to_test": ["x"]})

    def test_safe_filter(self):
        diff = ("diff --git a/.env b/.env\n+secret=abc\n"
                "diff --git a/app.py b/app.py\n+email=hello@example.com\n+api_key=abcd\n")
        filtered, omitted = main.filter_diff(diff, 10, 200)
        self.assertTrue(omitted)
        self.assertNotIn(".env", filtered)
        self.assertNotIn("hello@example.com", filtered)
        self.assertNotIn("abcd", filtered)
        self.assertIn("app.py", filtered)

    def test_empty_and_staged_git_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                subprocess.run(["git", "init", "-q"], check=True)
                self.assertIsNone(main.collect_changes(False))
                Path("example.py").write_text("print('hello')\n")
                with self.assertRaisesRegex(main.ToolError, "git add"):
                    main.collect_changes(False)
                subprocess.run(["git", "add", "example.py"], check=True)
                changes = main.collect_changes(True)
                self.assertIn("print('hello')", changes.diff)
                self.assertEqual(changes.file_count, 1)
            finally:
                os.chdir(previous)

    def test_one_api_request_and_cli_output(self):
        payload = json.dumps({"choices": [{"message": {"content": json.dumps({
            "title": "fix: 오류 수정", "why": ["오류 발생"], "what": ["수정"], "how_to_test": ["실행 확인"]
        })}}]}).encode()
        change = main.Changes(" M app.py", "diff --git a/app.py b/app.py\n+fix", 1, 2, False)
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(json.loads(request.data))
            return FakeResponse(payload)

        stdout = io.StringIO()
        with patch.object(main, "collect_changes", return_value=change), patch.dict(os.environ, {"AI_API_KEY": "dummy"}), patch.object(main, "urlopen", fake_urlopen), contextlib.redirect_stdout(stdout):
            self.assertEqual(main.main(["pr", "--temperature", "0.4", "--max-tokens", "150"]), 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["temperature"], 0.4)
        self.assertEqual(calls[0]["max_completion_tokens"], 150)
        self.assertIn("## How to Test", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
