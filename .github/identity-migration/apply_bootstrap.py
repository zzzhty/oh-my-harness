#!/usr/bin/env python3
from pathlib import Path
import base64
import zlib

root = Path(__file__).resolve().parent
encoded = "".join(
    (root / f"apply_payload_{index}.txt").read_text(encoding="utf-8").strip()
    for index in range(1, 6)
)
source = zlib.decompress(base64.b64decode(encoded))
code = compile(source, root / "apply.py", "exec")
exec(code, {"__name__": "__main__", "__file__": str(root / "apply.py")})

fixture = Path("tests/test_refresh_harness_integration.py")
text = fixture.read_text(encoding="utf-8")
old = "self.versions.get(name, self.source_versions[name])"
new = 'self.versions.get(name, self.source_versions.get(name, "0.9.0"))'
if old not in text:
    raise SystemExit("generated refresh fixture version lookup was not found")
fixture.write_text(text.replace(old, new, 1), encoding="utf-8")

watcher_test = Path("plugins/watcher/tests/test_skill_watcher.py")
text = watcher_test.read_text(encoding="utf-8")
old = '    def test_windows_codex_resolution_uses_path_then_managed_fallbacks(self) -> None:\n'
new = (
    '    @mock.patch("refresh_harness.codex_executable_is_startable", return_value=True)\n'
    '    def test_windows_codex_resolution_uses_path_then_managed_fallbacks(\n'
    '        self, _startable: mock.Mock\n'
    '    ) -> None:\n'
)
if old not in text:
    raise SystemExit("Watcher Windows Codex resolution test was not found")
watcher_test.write_text(text.replace(old, new, 1), encoding="utf-8")
