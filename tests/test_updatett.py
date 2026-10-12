"""Exercise the updater using isolated fake executables, never installed tools."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "updatett"
MOCK = r"""
import json, os, subprocess, sys, time
from pathlib import Path
name = Path(sys.argv[0]).name
root = Path(os.environ['TEST_ROOT'])
args = sys.argv[1:]
target = args[2] if name == 'uv' and args[:2] == ['tool', 'upgrade'] else name
if args == ['--version']:
    if name == 'wrangler' and os.environ.get('WRANGLER_WRITE_LOGS') != '0':
        sys.exit(23)
    if name == os.environ.get('TEST_UNKNOWN'):
        print('unrecognized version')
    elif name == 'op':
        print(os.environ.get('TEST_NEXT_OP_VERSION', '2.40.0') if globals().get('installed') else os.environ.get('TEST_OP_VERSION', '2.39.0'))
    else:
        state = root / ('version-' + name)
        print(state.read_text() if state.exists() else '1.0.0')
    sys.exit(0)
with (root / 'calls').open('a') as f:
    f.write(json.dumps([name] + args) + '\n')
if name == 'pgrep':
    if len(args) >= 4 and args[:1] == ['-u']:
        if args[-2:] == ['-x', 'op'] and os.environ.get('TEST_OP_IN_USE') == '1':
            print('999999')
            sys.exit(0)
        sys.exit(1)
    os.execv('/usr/bin/pgrep', ['/usr/bin/pgrep'] + args)
if name == 'pkgutil':
    if os.environ.get('TEST_BAD_PACKAGE') == '1':
        sys.exit(19)
    if args[0] == '--expand-full':
        candidate = Path(args[2]) / 'op.pkg/Payload/op'
        candidate.parent.mkdir(parents=True)
        candidate.write_text((root / 'bin/op').read_text().replace('name = Path', 'installed = True\nname = Path', 1))
        candidate.chmod(0o755)
    sys.exit(0)
if name == 'codesign':
    if os.environ.get('TEST_BAD_SIGNATURE') == '1':
        sys.exit(20)
    if args[-1] == str(root / 'bin/op'):
        if os.environ.get('TEST_FAIL_INSTALLED_VERIFY') == '1':
            sys.exit(21)
        if os.environ.get('TEST_BLOCK_INSTALLED_VERIFY') == '1':
            child = subprocess.Popen(['/bin/sleep', '30'])
            (root / 'worker').write_text(json.dumps([os.getpid(), child.pid]))
            time.sleep(30)
    sys.exit(0)
if target == os.environ.get('TEST_BLOCK'):
    child = subprocess.Popen(['/bin/sleep', '30'])
    (root / 'worker').write_text(json.dumps([os.getpid(), child.pid]))
    time.sleep(30)
if target == os.environ.get('TEST_FAIL'):
    print('simulated failure', file=sys.stderr)
    sys.exit(17)
if name == 'op':
    if os.environ.get('TEST_OP_DOWNLOAD') == '1':
        dest = Path(args[args.index('--directory') + 1])
        (dest / 'op.pkg').write_text('fake package')
elif os.environ.get('TEST_UNCHANGED') != '1':
    (root / ('version-' + ('wrangler' if name == 'npm' else target))).write_text('1.1.0')
"""


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="updatett-test-")
        self.root = Path(self.directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in [
            "uv",
            "ruff",
            "ty",
            "claude",
            "codex",
            "wrangler",
            "npm",
            "op",
            "pkgutil",
            "codesign",
            "pgrep",
        ]:
            executable = self.bin / name
            executable.write_text("#!" + sys.executable + "\n" + MOCK)
            executable.chmod(0o755)
        # The test copy omits only the workstation PATH prepend. NVM_DIR points
        # at a fixture, so the real user startup and executables cannot run.
        source = SOURCE.read_text()
        prepend = 'export PATH="$HOME/.local/bin:$PATH"'
        self.assertEqual(source.count(prepend), 1)
        self.script = self.root / "updatett"
        self.script.write_text(source.replace(prepend, ""))
        self.env = dict(
            os.environ,
            PATH=str(self.bin) + ":/usr/bin:/bin",
            TMPDIR=str(self.root),
            NVM_DIR=str(self.root / "nvm"),
            TEST_ROOT=str(self.root),
        )
        self.process = None

    def tearDown(self):
        if self.process:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            self.process.wait()
        self.directory.cleanup()

    def run_updater(self, **settings):
        return subprocess.run(
            ["/bin/zsh", "-f", str(self.script)],
            check=False,
            env=dict(self.env, **settings),
            capture_output=True,
            text=True,
            timeout=10,
        )

    def calls(self):
        return [
            json.loads(line) for line in (self.root / "calls").read_text().splitlines()
        ]

    def start_blocked(self):
        self.process = subprocess.Popen(
            ["/bin/zsh", "-f", str(self.script)],
            env=dict(self.env, TEST_BLOCK="uv"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + 5
        while not (self.root / "worker").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        return json.loads((self.root / "worker").read_text())

    def test_updates_and_no_logs_or_duplicate_rows(self):
        result = self.run_updater()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("OpenAI Codex"), 1)
        self.assertNotIn("\x1b", result.stdout)
        self.assertIn("1.0.0 → 1.1.0", result.stdout)
        calls = self.calls()
        self.assertIn(["codex", "update"], calls)
        self.assertIn(["uv", "tool", "upgrade", "ruff"], calls)
        npm = next(call for call in calls if call[0] == "npm")
        self.assertIn("wrangler@latest", npm)
        self.assertIn("--logs-max=0", npm)
        self.assertIn("--allow-scripts=esbuild,workerd,fsevents", npm)
        self.assertIn("--strict-allow-scripts", npm)
        self.assertFalse(list(self.root.glob("*.log")))
        self.assertFalse(list(self.root.glob("updatett-op.*")))

    def test_failure_continues_and_returns_nonzero(self):
        result = self.run_updater(TEST_FAIL="ruff")
        self.assertEqual(result.returncode, 1)
        self.assertIn("exit 17", result.stdout)
        self.assertIn(["codex", "update"], self.calls())

    def test_missing_and_unreadable_versions_fail(self):
        (self.bin / "ruff").unlink()
        result = self.run_updater(TEST_UNKNOWN="ty")
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing (ruff)", result.stdout)
        self.assertIn("version check failed", result.stdout)

    def test_unchanged_is_not_claimed_latest(self):
        result = self.run_updater(TEST_UNCHANGED="1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("(unchanged)", result.stdout)
        self.assertNotIn("already latest", result.stdout)

    def test_beta_download_is_verified_installed_and_removed(self):
        result = self.run_updater(
            TEST_OP_VERSION="2.42.0-beta.01",
            TEST_NEXT_OP_VERSION="2.42.0-beta.02",
            TEST_OP_DOWNLOAD="1",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("2.42.0-beta.01 → 2.42.0-beta.02", result.stdout)
        op = next(call for call in self.calls() if call[0] == "op")
        self.assertEqual(op[1:4], ["update", "--channel", "beta"])
        verification = [call for call in self.calls() if call[0] == "codesign"]
        self.assertEqual(len(verification), 2)
        self.assertTrue(all("2BUA8C4S2C" in call[3] for call in verification))
        self.assertFalse(list(self.root.glob("updatett-op.*")))

    def test_rejected_packages_and_busy_binary_are_not_installed(self):
        original = (self.bin / "op").read_bytes()
        for setting in ["TEST_BAD_PACKAGE", "TEST_BAD_SIGNATURE", "TEST_OP_IN_USE"]:
            with self.subTest(setting=setting):
                result = self.run_updater(**{setting: "1", "TEST_OP_DOWNLOAD": "1"})
                self.assertEqual(result.returncode, 1)
                self.assertEqual((self.bin / "op").read_bytes(), original)
                self.assertFalse(list(self.root.glob("updatett-op.*")))

    def test_failed_installed_verification_restores_previous_binary(self):
        original = (self.bin / "op").read_bytes()
        result = self.run_updater(TEST_OP_DOWNLOAD="1", TEST_FAIL_INSTALLED_VERIFY="1")
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.bin / "op").read_bytes(), original)
        self.assertFalse(list(self.root.glob("updatett-op.*")))

    def test_cancelled_install_restores_previous_binary_and_cleans_download(self):
        original = (self.bin / "op").read_bytes()
        self.process = subprocess.Popen(
            ["/bin/zsh", "-f", str(self.script)],
            env=dict(self.env, TEST_OP_DOWNLOAD="1", TEST_BLOCK_INSTALLED_VERIFY="1"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + 5
        while not (self.root / "worker").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue((self.root / "worker").exists())
        self.assertNotEqual((self.bin / "op").read_bytes(), original)
        self.process.send_signal(signal.SIGTERM)
        self.assertEqual(self.process.wait(timeout=5), 143)
        self.assertEqual((self.bin / "op").read_bytes(), original)
        self.assertFalse(list(self.root.glob("updatett-op.*")))

    def test_default_nvm_failure_does_not_use_inherited_npm(self):
        nvm = self.root / "nvm"
        nvm.mkdir()
        (nvm / "nvm.sh").write_text(
            'nvm() { [[ "$1 $2" == "use default" ]] && return 3; }\n'
        )
        result = self.run_updater()
        self.assertEqual(result.returncode, 1)
        self.assertIn("default Node unavailable", result.stdout)
        self.assertFalse(any(call[0] == "npm" for call in self.calls()))

    def test_lock_excludes_concurrent_run_and_recovers_after_crash(self):
        self.start_blocked()
        result = self.run_updater()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Another updatett", result.stderr)
        assert self.process is not None
        os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait()
        self.assertEqual(self.run_updater().returncode, 0)

    def test_signals_cancel_worker_and_descendant(self):
        for sig in [signal.SIGTERM, signal.SIGINT]:
            with self.subTest(signal=sig):
                (self.root / "worker").unlink(missing_ok=True)
                pids = self.start_blocked()
                assert self.process is not None
                self.process.send_signal(sig)
                self.assertEqual(self.process.wait(timeout=5), 128 + sig)
                for pid in pids:
                    status = subprocess.run(
                        ["/bin/ps", "-o", "stat=", "-p", str(pid)],
                        check=False,
                        capture_output=True,
                        text=True,
                    ).stdout.strip()
                    self.assertTrue(not status or status.startswith("Z"), (pid, status))
                self.assertEqual(self.run_updater().returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
