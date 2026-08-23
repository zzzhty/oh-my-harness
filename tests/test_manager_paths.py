from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from manager_paths import manager_home, venv_path, venv_python  # noqa: E402


class ManagerPathTests(unittest.TestCase):
    def test_default_home_and_venv_are_harness_neutral(self) -> None:
        home = manager_home(environ={}, user_home=Path("/users/tester"))
        self.assertEqual(home, Path("/users/tester/.oh-my-harness"))
        self.assertEqual(venv_path(home), Path("/users/tester/.oh-my-harness/venv"))

    def test_environment_override_is_the_manager_root_itself(self) -> None:
        home = manager_home(
            environ={"OH_MY_HARNESS_HOME": "/srv/omh"},
            user_home=Path("/ignored"),
        )
        self.assertEqual(home, Path("/srv/omh"))

    def test_empty_environment_override_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            manager_home(
                environ={"OH_MY_HARNESS_HOME": "  "},
                user_home=Path("/users/tester"),
            )

    def test_relative_override_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be an absolute path"):
            manager_home(
                environ={"OH_MY_HARNESS_HOME": "relative/home"},
                user_home=Path("/users/tester"),
            )

    def test_venv_interpreter_uses_the_platform_layout(self) -> None:
        path = venv_python(Path("/manager/venv"))
        expected = (
            Path("/manager/venv/Scripts/python.exe")
            if sys.platform == "win32"
            else Path("/manager/venv/bin/python")
        )
        self.assertEqual(path, expected)


if __name__ == "__main__":
    unittest.main()
