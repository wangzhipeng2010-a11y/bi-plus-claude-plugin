from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "send-feishu-file"
REAL_BACKEND_CMD = "/opt/bi-plus/bin/send-feishu-file"


def make_fake_backend(stdout_text: str, exit_code: int) -> str:
    """Write a temp shell script that mimics the backend command."""
    safe_text = stdout_text.replace("'", "'\\''")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(f"#!/bin/sh\nprintf '%s\\n' '{safe_text}'\nexit {exit_code}\n")
        path = f.name
    os.chmod(path, stat.S_IRWXU)
    return path


def run_script(
    *args,
    backend_cmd: str | None = None,
    backend_timeout: str | None = None,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if backend_cmd is not None:
        env["BI_PLUS_BACKEND_CMD"] = backend_cmd
    if backend_timeout is not None:
        env["BI_PLUS_BACKEND_TIMEOUT"] = backend_timeout
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class SendFeishuFileTests(unittest.TestCase):
    def test_named_flag_exit0_and_message(self):
        backend = make_fake_backend("文件已发送到你的飞书", 0)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "文件已发送到你的飞书")

    def test_positional_arg_exit0_and_message(self):
        backend = make_fake_backend("文件已发送到你的飞书", 0)
        try:
            result = run_script("reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "文件已发送到你的飞书")

    def test_relative_path_passed_verbatim(self):
        """Plugin must not resolve relative path to absolute."""
        # Fake backend echoes its first path arg so we can verify what it received.
        # The plugin separates options from the path with `--`; skip it here.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/sh\n[ \"$1\" = \"--\" ] && shift\nprintf '%s\\n' \"$1\"\nexit 0\n")
            backend = f.name
        os.chmod(backend, stat.S_IRWXU)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertEqual(result.stdout.strip(), "reports/a.csv")

    def test_no_extra_params_injected(self):
        """Plugin must not inject open_id, uid, recipient, or HTTP URL."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            # Print all args (after the `--` separator) so we can inspect them.
            f.write("#!/bin/sh\n[ \"$1\" = \"--\" ] && shift\nfor a in \"$@\"; do printf '%s\\n' \"$a\"; done\nexit 0\n")
            backend = f.name
        os.chmod(backend, stat.S_IRWXU)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        args_out = result.stdout.lower()
        for forbidden in ("open_id", "uid", "recipient", "http"):
            self.assertNotIn(forbidden, args_out)

    def test_type_aware_delivery_stays_backend_owned(self):
        """Markdown/CSV/Excel paths still pass through as plain paths.

        The backend decides whether to deliver them as Feishu docs, sheets, or
        files; the plugin must not add local conversion flags.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/sh\n[ \"$1\" = \"--\" ] && shift\nprintf '%s\\n' \"$*\"\nexit 0\n")
            backend = f.name
        os.chmod(backend, stat.S_IRWXU)
        try:
            for path in (
                "docs/analysis.md",
                "reports/recharge.csv",
                "reports/recharge.xls",
                "reports/recharge.xlsx",
                "exports/result.pdf",
            ):
                with self.subTest(path=path):
                    result = run_script("--file", path, backend_cmd=backend)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(result.stdout.strip(), path)
        finally:
            os.unlink(backend)

    def test_backend_exit0_means_plugin_exit0(self):
        backend = make_fake_backend("文件已发送到你的飞书", 0)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertEqual(result.returncode, 0)

    def test_backend_nonzero_means_plugin_nonzero(self):
        backend = make_fake_backend("你还没有发送权限", 1)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "你还没有发送权限")

    def test_backend_stdout_shown_verbatim(self):
        backend = make_fake_backend("文件不在允许目录", 1)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertEqual(result.stdout.strip(), "文件不在允许目录")

    def test_backend_command_not_found(self):
        result = run_script("--file", "reports/a.csv", backend_cmd="/nonexistent/send-feishu-file")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "暂时无法连接 BI Plus 后台服务")

    def test_backend_empty_stdout_shows_fallback(self):
        backend = make_fake_backend("", 1)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend)
        finally:
            os.unlink(backend)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "暂时无法连接 BI Plus 后台服务")

    def test_no_path_shows_invalid_request(self):
        result = run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "请求格式不正确")
        self.assertEqual(result.stderr, "")

    def test_leading_dash_path_passed_as_file_not_option(self):
        """A path starting with '-' must reach the backend as the file arg, not be
        parsed as an option. The plugin guards this with a '--' separator."""
        # Backend mimics the real argparse contract: positional file_path + --socket.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                "import argparse\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('file_path')\n"
                "p.add_argument('--socket', default='')\n"
                "a = p.parse_args()\n"
                "print(a.file_path)\n"
            )
            backend_py = f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(f"#!/bin/sh\nexec {sys.executable} {backend_py} \"$@\"\n")
            backend = f.name
        os.chmod(backend, stat.S_IRWXU)
        try:
            # Equals-form so the leading-dash value reaches the plugin intact.
            result = run_script("--file=--socket=/tmp/evil.sock", backend_cmd=backend)
        finally:
            os.unlink(backend)
            os.unlink(backend_py)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "--socket=/tmp/evil.sock")

    def test_non_utf8_locale_does_not_crash(self):
        """A non-UTF-8 server locale must not crash on reading or printing
        the backend's Chinese output."""
        backend = make_fake_backend("文件已发送到你的飞书", 0)
        try:
            result = run_script(
                "--file",
                "reports/a.csv",
                backend_cmd=backend,
                extra_env={"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0"},
            )
        finally:
            os.unlink(backend)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "文件已发送到你的飞书")
        self.assertEqual(result.stderr, "")

    def test_backend_timeout_shows_fallback(self):
        # Backend sleeps longer than the plugin's timeout.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/sh\nsleep 5\nprintf '%s\\n' '文件已发送到你的飞书'\n")
            backend = f.name
        os.chmod(backend, stat.S_IRWXU)
        try:
            result = run_script("--file", "reports/a.csv", backend_cmd=backend, backend_timeout="0.3")
        finally:
            os.unlink(backend)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "暂时无法连接 BI Plus 后台服务")


if __name__ == "__main__":
    unittest.main()
