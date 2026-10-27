from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/doc-alignment/scripts/audit_docs.py"


class DocAuditEntryTests(unittest.TestCase):
    def test_explicit_audit_lifecycle_leaves_target_and_old_state_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="doc audit 空格 ") as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "README.md").write_text("# Demo\n[broken](missing.md)\n")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test",
                            "-c", "user.email=test@example.com", "commit", "-qm", "fixture"], check=True)
            old = root / "home/.codex/watcher/doc/reports"
            old.mkdir(parents=True)
            marker = old / "old.md"
            marker.write_bytes(b"historical report must remain untouched")
            config = root / "repos.json"
            config.write_text(json.dumps({"repos": [{"name": "demo", "path": str(repo),
                              "docs": ["README.md"], "commit_threshold": 5}]}))
            state = root / "new audit state"
            env = {k: v for k, v in os.environ.items() if k != "DOC_ALIGNMENT_STATE_DIR"}
            env.update(HOME=str(root / "home"), USERPROFILE=str(root / "home"),
                       CODEX_HOME=str(root / "home/.codex"), WATCHER_DOC_STATE_DIR=str(old.parent),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="cp1252")

            def run(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                                      env=env, cwd=root, capture_output=True, text=True, encoding="utf-8")

            before = (repo / "README.md").read_bytes()
            help_result = run("--help")
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            missing = run("doctor", "--config", str(config))
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("set --state-dir", missing.stderr)
            self.assertFalse(state.exists())
            doctor = run("doctor", "--config", str(config), "--state-dir", str(state))
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertIn(str(repo), doctor.stdout)
            self.assertIn(str(state), doctor.stdout)
            report = run("report", "--config", str(config), "--state-dir", str(state),
                         "--mode", "commit-dependent", "--mark-audited", "--digest")
            self.assertEqual(report.returncode, 0, report.stdout + report.stderr)
            self.assertTrue(list((state / "reports").glob("*.md")))
            preview = run("commit-counter", "--config", str(config), "--state-dir", str(state))
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertIn("demo: skip", preview.stdout)
            self.assertEqual((repo / "README.md").read_bytes(), before)
            self.assertEqual(marker.read_bytes(), b"historical report must remain untouched")
            self.assertEqual(list(old.parent.rglob("*")), [old, marker])
            status = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True)
            self.assertEqual(status, "")
            self.assertFalse(list(root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
