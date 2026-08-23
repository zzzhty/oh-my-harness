from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import repo_skill_catalog  # noqa: E402


def write_skill(
    repo_root: Path,
    plugin: str,
    directory_name: str,
    *,
    catalog_name: str | None = None,
) -> Path:
    skill_dir = repo_root / "plugins" / plugin / "skills" / directory_name
    skill_dir.mkdir(parents=True)
    name = catalog_name or directory_name
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test skill\n---\n",
        encoding="utf-8",
    )
    return skill_dir


class RepoSkillCatalogTests(unittest.TestCase):
    def test_catalog_uses_frontmatter_name_without_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            source = write_skill(root, "alpha", "physical-name", catalog_name="catalog-name")
            marketplace = root / ".agents" / "plugins" / "marketplace.json"
            marketplace.parent.mkdir(parents=True)
            marketplace.write_text("not json", encoding="utf-8")

            catalog = repo_skill_catalog.load_repo_skill_catalog(root)

        self.assertEqual(len(catalog.sources), 1)
        self.assertEqual(catalog.sources[0].name, "catalog-name")
        self.assertEqual(catalog.sources[0].directory_name, "physical-name")
        self.assertEqual(catalog.sources[0].path, source.resolve())

    def test_duplicate_catalog_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write_skill(root, "alpha", "one", catalog_name="shared")
            write_skill(root, "beta", "two", catalog_name="shared")
            with self.assertRaisesRegex(SystemExit, "duplicate catalog skill names"):
                repo_skill_catalog.load_repo_skill_catalog(root)

    def test_missing_or_malformed_frontmatter_is_rejected(self) -> None:
        cases = {
            "missing-file": None,
            "missing-frontmatter": "# no frontmatter\n",
            "invalid-yaml": "---\nname: [\n---\n",
            "unsafe-name": "---\nname: ../escape\n---\n",
        }
        for label, content in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "repo"
                skill_dir = root / "plugins" / "alpha" / "skills" / label
                skill_dir.mkdir(parents=True)
                if content is not None:
                    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
                with self.assertRaises(SystemExit):
                    repo_skill_catalog.load_repo_skill_catalog(root)

    def test_skill_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            outside = write_skill(base / "outside", "alpha", "escaped")
            skills_root = root / "plugins" / "alpha" / "skills"
            skills_root.mkdir(parents=True)
            try:
                (skills_root / "escaped").symlink_to(outside, target_is_directory=True)
            except OSError as exc:  # pragma: no cover - platform privilege boundary
                self.skipTest(f"directory symlinks unavailable: {exc}")
            with self.assertRaisesRegex(SystemExit, "escapes repository authority"):
                repo_skill_catalog.load_repo_skill_catalog(root)

    def test_live_catalog_matches_all_repository_skill_frontmatter_names(self) -> None:
        catalog = repo_skill_catalog.load_repo_skill_catalog()
        self.assertGreaterEqual(len(catalog.sources), 30)
        self.assertEqual(len(catalog.sources), len(catalog.by_name))
        self.assertEqual(
            set(catalog.plugin_names),
            {"watcher", "workflow", "mattpocock-skills"},
        )
        for source in catalog.sources:
            self.assertTrue((source.path / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
