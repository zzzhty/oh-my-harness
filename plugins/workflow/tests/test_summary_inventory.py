"""Behavioral coverage for the summary inventory command's selected scope."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


COLLECTOR = (Path(__file__).resolve().parents[1] / "skills" / "summary-in-html" /
             "scripts" / "collect_summary_inputs.py")


class SummaryInventoryTests(unittest.TestCase):
    def test_cli_does_not_follow_descendant_links_outside_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / "repo"
            scope = root / "selected"
            scope.mkdir(parents=True)
            (scope / "README.md").write_text("included", encoding="utf-8")
            (root / "sibling.py").write_text("out of scope", encoding="utf-8")
            external = parent / "external"
            external.mkdir()
            (external / "external.py").write_text("outside repository", encoding="utf-8")
            try:
                (scope / "sibling.py").symlink_to(root / "sibling.py")
                (scope / "external.py").symlink_to(external / "external.py")
                (scope / "alias").symlink_to(external, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symbolic link fixture unavailable: {exc}")

            result = subprocess.run(
                [sys.executable, "-B", str(COLLECTOR), "--root", str(root), "--scope", "selected"],
                check=True, capture_output=True, text=True, encoding="utf-8",
            )
            (inventory,) = json.loads(result.stdout)["scopes"]
            self.assertEqual([row["path"] for row in inventory["files"]], ["selected/README.md"])
            self.assertEqual(inventory["directories"], [])
            self.assertEqual(inventory["file_count_seen"], 1)
