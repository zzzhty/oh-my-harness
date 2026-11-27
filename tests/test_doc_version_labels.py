"""Regression coverage through the same architecture entry point used by CI."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_architecture as arch

EMPTY = {"file_lines": {}, "text_io_utf8": {}, "ruff": []}


class DocVersionLabelTests(unittest.TestCase):
    def check_files(self, files: dict[str, str]):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, source in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
            return arch.check(root, EMPTY, ruff=False)

    def test_fails_on_filename_and_numbered_headings(self):
        items = self.check_files({
            "README.md": "# Rollout Revision + 03\n\n## Guide Rev_2\n\nGuide revision #4\n===\n",
            "docs/installer-v3.md": "# Installer\n",
            "plugins/workflow/skills/sample/SKILL.md": "# 方案revision+2\n",
        })
        self.assertEqual(arch.exit_code(items), 1)
        self.assertEqual([(item.path, item.line, item.rule) for item in items], [
            ("README.md", 1, "doc-version-label"),
            ("README.md", 3, "doc-version-label"),
            ("README.md", 5, "doc-version-label"),
            ("docs/installer-v3.md", 1, "doc-version-label"),
            ("plugins/workflow/skills/sample/SKILL.md", 1, "doc-version-label"),
        ])
        self.assertIn("'Revision + 03'", items[0].render())
        self.assertIn("Fix:", items[0].render())

    def test_preserves_release_tags_archives_and_non_title_mentions(self):
        label = "# Old plan revision+2\n"
        files = {
            "CHANGELOG.md": label,
            "docs/releases/revision-3.md": label,
            "docs/archive/revision-3.md": label,
            "docs/adr/archive/revision-3.md": label,
            "dev_docs/archive/revision-3.md": label,
            ".github/workflows/actions.yml": "uses: actions/checkout@v4\n",
            "docs/upgrade-v2.10.3-rc.1.md": "# Upgrade to v2.10.3-rc.1\n\nWe previously used revision 4.\n",
            "docs/examples.md": (
                "---\nname: legacy-v2\n---\n"
                "\n````markdown\n```\n# Example rev2\n````\n"
                "\n~~~ markdown\n# Example v3\n~~~~\n"
                "\n<!--\n# Hidden v2\n-->\n# Visible <!-- hidden rev3 -->\n"
            ),
        }
        self.assertEqual(self.check_files(files), [])

    def test_exception_matches_only_the_named_heading_token(self):
        items = self.check_files({
            "docs/api.md": (
                "# Vendor API v4 <!-- doc-version-label: allow v4; Vendor API contract -->\n"
                "## Vendor API v4 revision+3 <!-- doc-version-label: allow v4; Vendor API contract -->\n"
                "## Vendor API v4\n"
            ),
        })
        self.assertEqual([item.line for item in items], [2, 3])
        self.assertIn("'revision+3'", items[0].violation)
        self.assertIn("'v4'", items[1].violation)

    def test_checks_rendered_link_labels_not_destinations(self):
        items = self.check_files({
            "docs/links.md": (
                "# [Install guide](https://example.org/vendor/v3/install)\n"
                "## [Install guide revision+3](https://example.org/vendor/current/install)\n"
                "## [Reference][vendor-v3]\n"
                "\n[vendor-v3]: https://example.org/vendor/v3/install\n"
            ),
        })
        self.assertEqual([(item.line, item.rule) for item in items], [(2, "doc-version-label")])
        self.assertIn("'revision+3'", items[0].violation)

    def test_checks_all_lines_of_a_multiline_setext_heading(self):
        items = self.check_files({
            "docs/design.md": "# Design\n\nInstall guide revision+3\nMigration notes\n===\n",
        })
        self.assertEqual([(item.line, item.rule) for item in items], [(3, "doc-version-label")])
        self.assertIn("'revision+3'", items[0].violation)
