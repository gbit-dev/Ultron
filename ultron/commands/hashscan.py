import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        print(f"path not found: {root}")
        return 1

    files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    by_hash: dict[str, list[str]] = {}
    manifest = []

    for p in files:
        digest = _sha256(p)
        manifest.append({"path": str(p), "size": p.stat().st_size, "sha256": digest})
        by_hash.setdefault(digest, []).append(str(p))

    dups = {h: paths for h, paths in by_hash.items() if len(paths) > 1}

    if args.json:
        out = {"files": manifest, "duplicates": dups}
        text = json.dumps(out, indent=2)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"wrote {args.output} ({len(files)} files, {len(dups)} duplicate groups)")
        else:
            print(text)
    else:
        print(f"{len(files)} files, {len(dups)} duplicate groups")
        for h, paths in dups.items():
            print(f"\n{h[:16]}…")
            for p in paths:
                print(f"  {p}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("hashscan", help="SHA-256 every file, group duplicates")
    p.add_argument("path", help="file or directory")
    p.add_argument("--json", action="store_true", help="emit JSON manifest")
    p.add_argument("--output", help="write JSON to this file")
    p.set_defaults(func=run)