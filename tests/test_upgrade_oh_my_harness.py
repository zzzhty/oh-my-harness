from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UPGRADE_SCRIPT = REPO_ROOT / "scripts" / "upgrade_oh_my_harness.sh"
POWERSHELL_UPGRADE_SCRIPT = REPO_ROOT / "scripts" / "upgrade_oh_my_harness.ps1"


def extension_platform_dir() -> str | None:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Linux":
        platform_name = "linux"
    elif system == "Darwin":
        platform_name = "macos"
    else:
        return None

    if machine in {"amd64", "x86_64"}:
        architecture = "x86_64"
    elif machine in {"aarch64", "arm64"}:
        architecture = "aarch64"
    else:
        return None
    return f"{platform_name}-{architecture}"


def write_fake_codex(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env sh\n"
        "if [ \"${1-}\" = \"--version\" ]; then\n"
        "    echo 'codex-cli 999.0.0-test'\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_python_proxy(path: Path, *, reject_harness_helpers: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rejection = (
        'case "${1-}" in\n'
        '    *refresh_harness.py|*check_harness.py)\n'
        '        echo "bootstrap Python has no PyYAML" >&2\n'
        '        exit 91\n'
        '        ;;\n'
        'esac\n'
        if reject_harness_helpers
        else ""
    )
    path.write_text(
        "#!/usr/bin/env sh\n"
        + rejection
        + f"exec {shlex.quote(sys.executable)} \"$@\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def write_noop_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


@unittest.skipIf(os.name == "nt", "Unix wrapper test")
class UnixUpgradeWrapperTests(unittest.TestCase):
    def run_upgrade(
        self,
        *,
        env: dict[str, str],
        codex_home: Path,
        harness: str | None = None,
        bootstrap_python: Path | str = sys.executable,
        tooling_python: Path | str | None = sys.executable,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [str(UPGRADE_SCRIPT)]
        if harness is not None:
            command.extend(["--harness", harness])
        command.extend([
            "--bootstrap-python",
            str(bootstrap_python),
            "--codex-home",
            str(codex_home),
            "--dry-run",
            "--skip-check",
        ])
        if tooling_python is not None:
            command.extend(["--tooling-python", str(tooling_python)])
        command.extend(extra_args or [])
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_bootstrap_python_without_yaml_never_runs_harness_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = user_home / ".oh-my-harness" / "venv" / "bin" / "python"
            write_python_proxy(bootstrap_python, reject_harness_helpers=True)
            write_python_proxy(tooling_python, reject_harness_helpers=False)
            env = os.environ.copy()
            env.update({"HOME": str(user_home), "PATH": "/usr/bin:/bin"})
            env.pop("CODEX_BIN", None)

            result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="zcode",
                bootstrap_python=bootstrap_python,
                tooling_python=None,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            f"+ {bootstrap_python} {REPO_ROOT / 'scripts' / 'bootstrap_tooling_env.py'}",
            result.stdout,
        )
        self.assertIn(
            f"+ {tooling_python} {REPO_ROOT / 'scripts' / 'refresh_harness.py'}",
            result.stdout,
        )
        self.assertNotIn("bootstrap Python has no PyYAML", result.stderr)

    def test_wrapper_prefers_complete_system_validator_then_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = root / "venv" / "bin" / "python"
            write_noop_executable(bootstrap_python)
            write_noop_executable(tooling_python)
            env = os.environ.copy()
            env.update({"HOME": str(root), "PATH": "/usr/bin:/bin"})
            env.pop("PLUGIN_VALIDATOR", None)

            fallback_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="zcode",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
            )
            system_scripts = (
                codex_home / "skills" / ".system" / "plugin-creator" / "scripts"
            )
            system_scripts.mkdir(parents=True)
            system_validator = system_scripts / "validate_plugin.py"
            system_validator.write_text("# validator fixture\n", encoding="utf-8")
            incomplete_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="zcode",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
            )
            (system_scripts / "identifier_validation.py").write_text(
                "# identifier fixture\n",
                encoding="utf-8",
            )
            system_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="zcode",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
            )
            env["PLUGIN_VALIDATOR"] = "/custom/validate_plugin.py"
            override_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="zcode",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
            )

        fallback_validator = REPO_ROOT / "scripts" / "validate_plugin.py"
        self.assertEqual(fallback_result.returncode, 0, fallback_result.stderr)
        self.assertIn(f"PLUGIN_VALIDATOR={fallback_validator}", fallback_result.stdout)
        self.assertEqual(incomplete_result.returncode, 0, incomplete_result.stderr)
        self.assertIn(f"PLUGIN_VALIDATOR={fallback_validator}", incomplete_result.stdout)
        self.assertEqual(system_result.returncode, 0, system_result.stderr)
        self.assertIn(f"PLUGIN_VALIDATOR={system_validator}", system_result.stdout)
        self.assertEqual(override_result.returncode, 0, override_result.stderr)
        self.assertIn(
            "PLUGIN_VALIDATOR=/custom/validate_plugin.py",
            override_result.stdout,
        )

    def test_yes_is_forwarded_to_registry_owned_confirmations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = user_home / ".oh-my-harness" / "venv" / "bin" / "python"
            write_noop_executable(bootstrap_python)
            write_noop_executable(tooling_python)
            env = os.environ.copy()
            env.update({"HOME": str(user_home), "PATH": "/usr/bin:/bin"})

            command = [
                str(UPGRADE_SCRIPT),
                "--harness",
                "zcode",
                "--bootstrap-python",
                str(bootstrap_python),
                "--codex-home",
                str(codex_home),
                "--tooling-python",
                str(tooling_python),
                "--skip-check",
            ]
            confirmed = subprocess.run(
                [*command, "--yes"],
                cwd=REPO_ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )

            self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
            self.assertIn("--harness zcode", confirmed.stdout)
            self.assertIn("--yes", confirmed.stdout)

    def test_omitted_harness_is_left_to_the_registry_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = user_home / ".oh-my-harness" / "venv" / "bin" / "python"
            write_noop_executable(bootstrap_python)
            write_noop_executable(tooling_python)
            env = os.environ.copy()
            env.update({"HOME": str(user_home), "PATH": "/usr/bin:/bin"})

            result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Harness=registry-default", result.stdout)
        refresh_line = next(
            line for line in result.stdout.splitlines() if "refresh_harness.py" in line
        )
        self.assertNotIn("--harness", refresh_line)

    def test_wrapper_delegates_codex_resolution_and_keeps_codex_bin_strict(self) -> None:
        platform_dir = extension_platform_dir()
        if platform_dir is None:
            self.skipTest("unsupported Codex extension platform")
        system_path = "/usr/bin:/bin"
        if shutil.which("codex", path=system_path):
            self.skipTest("test PATH unexpectedly contains codex")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            standalone_cli = codex_home / "packages" / "standalone" / "current" / "bin" / "codex"
            extension_cli = (
                user_home
                / ".vscode-server"
                / "extensions"
                / "openai.chatgpt-1.2.3"
                / "bin"
                / platform_dir
                / "codex"
            )
            write_fake_codex(standalone_cli)
            write_fake_codex(extension_cli)

            env = os.environ.copy()
            env.update({"HOME": str(user_home), "PATH": system_path})
            env.pop("CODEX_BIN", None)
            env.pop("CODEX_HOME", None)
            env.pop("CODEX_INSTALL_DIR", None)

            standalone_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="codex",
            )
            self.assertEqual(standalone_result.returncode, 0, standalone_result.stderr)
            self.assertIn("CodexPath=auto-if-required-by-harness", standalone_result.stdout)
            self.assertIn(str(standalone_cli), standalone_result.stdout)
            self.assertIn("--harness codex", standalone_result.stdout)

            standalone_cli.unlink()
            extension_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="codex",
                extra_args=["--codex", str(extension_cli)],
            )
            self.assertEqual(extension_result.returncode, 0, extension_result.stderr)
            self.assertIn(str(extension_cli), extension_result.stdout)

            env["CODEX_BIN"] = str(root / "missing-configured-codex")
            strict_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="codex",
            )
            self.assertNotEqual(strict_result.returncode, 0)
            self.assertIn("executable not found. Checked:", strict_result.stderr)
            self.assertIn(env["CODEX_BIN"], strict_result.stderr)

    def test_invalid_distribution_fails_before_codex_resolution_in_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            shutil.copytree(
                REPO_ROOT,
                repo,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            marketplace = repo / ".agents" / "plugins" / "marketplace.json"
            payload = json.loads(marketplace.read_text(encoding="utf-8"))
            payload["plugins"][0]["policy"]["installation"] = "INSTALLED_BY_DEFAULT"
            marketplace.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            user_home = root / "home"
            codex_home = user_home / ".codex"
            missing_codex = root / "missing-codex"
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(user_home),
                    "PATH": "/usr/bin:/bin",
                    "CODEX_BIN": str(missing_codex),
                }
            )
            result = subprocess.run(
                [
                    str(repo / "scripts" / "upgrade_oh_my_harness.sh"),
                    "--harness",
                    "codex",
                    "--bootstrap-python",
                    sys.executable,
                    "--codex-home",
                    str(codex_home),
                    "--tooling-python",
                    sys.executable,
                    "--dry-run",
                    "--skip-check",
                ],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installation policy must be 'AVAILABLE'", result.stderr)
        self.assertNotIn("executable not found", result.stderr)
        self.assertNotIn(str(missing_codex), result.stderr)

    def test_retired_prune_option_is_rejected_before_executable_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = os.environ.copy()
            env.update({"HOME": str(root / "home"), "PATH": "/usr/bin:/bin"})
            env["CODEX_BIN"] = str(root / "missing-codex")
            result = subprocess.run(
                [str(UPGRADE_SCRIPT), "--prune-plugins", "--dry-run", "--skip-check"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option: --prune-plugins", result.stderr)
        self.assertNotIn(str(root / "missing-codex"), result.stderr)

    def test_legacy_discovery_profile_option_is_rejected(self) -> None:
        result = subprocess.run(
            [str(UPGRADE_SCRIPT), "--discovery-profile", "universal"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option: --discovery-profile", result.stderr)

    def test_retired_skill_mode_option_is_rejected(self) -> None:
        result = subprocess.run(
            [str(UPGRADE_SCRIPT), "--skill-mode", "universal"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option: --skill-mode", result.stderr)

    def test_native_harness_does_not_require_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = user_home / ".oh-my-harness" / "venv" / "bin" / "python"
            write_noop_executable(bootstrap_python)
            write_noop_executable(tooling_python)
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(user_home),
                    "PATH": "/usr/bin:/bin",
                    "CODEX_BIN": str(root / "missing-codex"),
                }
            )
            result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="zcode",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CodexPath=auto-if-required-by-harness", result.stdout)
        self.assertIn("--harness zcode", result.stdout)

    def test_wrapper_only_forwards_git_ref_when_the_user_supplies_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = user_home / ".oh-my-harness" / "venv" / "bin" / "python"
            write_noop_executable(bootstrap_python)
            write_noop_executable(tooling_python)
            env = os.environ.copy()
            env.update({"HOME": str(user_home), "PATH": "/usr/bin:/bin"})

            default_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="codex",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
            )
            explicit_result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="codex",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
                extra_args=["--git-ref", "release"],
            )

        self.assertEqual(default_result.returncode, 0, default_result.stderr)
        self.assertNotIn("--git-ref", default_result.stdout)
        self.assertEqual(explicit_result.returncode, 0, explicit_result.stderr)
        self.assertIn("--git-ref release", explicit_result.stdout)

    def test_wrapper_forwards_the_explicit_repo_relocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_home = root / "home"
            codex_home = user_home / ".codex"
            bootstrap_python = root / "bin" / "bootstrap-python"
            tooling_python = user_home / ".oh-my-harness" / "venv" / "bin" / "python"
            former_repo = root / "former-repo"
            write_noop_executable(bootstrap_python)
            write_noop_executable(tooling_python)
            env = os.environ.copy()
            env.update({"HOME": str(user_home), "PATH": "/usr/bin:/bin"})

            result = self.run_upgrade(
                env=env,
                codex_home=codex_home,
                harness="codex",
                bootstrap_python=bootstrap_python,
                tooling_python=tooling_python,
                extra_args=["--migrate-from-repo", str(former_repo)],
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"--migrate-from-repo {former_repo}", result.stdout)


class PowerShellUpgradeWrapperContractTests(unittest.TestCase):
    def test_registry_default_is_not_duplicated_and_explicit_harness_is_forwarded(self) -> None:
        script = POWERSHELL_UPGRADE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[string]$Harness,", script)
        self.assertNotIn('[string]$Harness = "codex"', script)
        self.assertNotIn("ValidateSet", script)
        self.assertNotIn("throw ", script.lower())
        self.assertIn("exit $ExitCode", script)
        self.assertIn("function Write-AccentError", script)
        self.assertIn("[Console]::IsErrorRedirected", script)
        self.assertIn("[Console]::ForegroundColor", script)
        self.assertIn("Test-Path Env:NO_COLOR", script)
        self.assertIn('$HarnessWasProvided = $PSBoundParameters.ContainsKey("Harness")', script)
        self.assertGreaterEqual(script.count('@("--harness", $Harness)'), 2)
        self.assertIn('Write-Host "Harness=registry-default"', script)
        self.assertNotIn("PrunePlugins", script)
        self.assertNotIn("DiscoveryProfile", script)
        self.assertIn('$GitRefWasProvided = $PSBoundParameters.ContainsKey("GitRef")', script)
        self.assertIn('if ($GitRefWasProvided)', script)
        self.assertIn('$CodexPathWasProvided = $PSBoundParameters.ContainsKey("CodexPath")', script)
        self.assertNotIn("Resolve-CodexCli", script)
        self.assertNotIn("Get-CodexCliFallbackCandidates", script)
        self.assertIn('"scripts\\bootstrap_tooling_env.py"', script)
        self.assertIn('"--skip-bootstrap"', script)
        self.assertIn("[switch]$Yes", script)
        self.assertIn('$refreshArgs += "--yes"', script)
        self.assertIn('@("--migrate-from-repo", $MigrateFromRepo)', script)
        self.assertIn('if (-not $env:PLUGIN_VALIDATOR)', script)
        self.assertIn('$systemPluginValidator', script)
        self.assertIn('$systemIdentifierValidator', script)
        self.assertIn(
            'Join-Path $env:CODEX_HOME "skills\\.system\\plugin-creator\\scripts\\validate_plugin.py"',
            script,
        )
        self.assertIn(
            'Join-Path $env:OH_MY_HARNESS_ROOT "scripts\\validate_plugin.py"',
            script,
        )
        self.assertLess(
            script.index('-Exe $BootstrapPython', script.index('$bootstrapArgs')),
            script.index('-Exe $env:OH_MY_HARNESS_PYTHON', script.index('$refreshArgs')),
        )

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell wrapper test",
    )
    def test_explicit_help_exits_before_bootstrap_or_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_python = Path(tmp) / "missing-python.exe"
            result = subprocess.run(
                [
                    shutil.which("powershell.exe") or "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL_UPGRADE_SCRIPT),
                    "-Help",
                    "-BootstrapPython",
                    str(missing_python),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: omh [-Harness ID] [options]", result.stdout)
        self.assertIn("-MigrateMarketplace", result.stdout)
        self.assertIn("-Help", result.stdout)
        self.assertNotIn("OH_MY_HARNESS_HOME=", result.stdout)
        self.assertNotIn(str(missing_python), result.stdout + result.stderr)

    @unittest.skipUnless(
        os.name == "nt" and shutil.which("powershell.exe"),
        "Windows PowerShell wrapper test",
    )
    def test_refresh_failure_preserves_reason_and_nonzero_exit_code_without_throwing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager_home = Path(tmp) / ".oh-my-harness"
            failing_python = Path(tmp) / "failing-python.cmd"
            failing_python.write_text(
                "@echo off\r\n"
                'if "%~1"=="scripts\\bootstrap_tooling_env.py" exit /b 0\r\n'
                "echo simulated refresh failure 1>&2\r\n"
                "exit /b 23\r\n",
                encoding="utf-8",
                newline="",
            )
            result = subprocess.run(
                [
                    shutil.which("powershell.exe") or "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(POWERSHELL_UPGRADE_SCRIPT),
                    "-ManagerHome",
                    str(manager_home),
                    "-BootstrapPython",
                    str(failing_python),
                    "-ToolingPython",
                    str(failing_python),
                    "-Harness",
                    "codex",
                    "-DryRun",
                    "-SkipCheck",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 23)
        self.assertIn("simulated refresh failure", result.stderr)
        self.assertIn(
            "error: oh-my-harness refresh failed with exit code 23",
            result.stderr,
        )
        self.assertNotIn("\x1b", result.stderr)
        self.assertNotIn("RuntimeException", result.stderr)
        self.assertNotIn("FullyQualifiedErrorId", result.stderr)
        self.assertNotIn("At ", result.stderr)


if __name__ == "__main__":
    unittest.main()
