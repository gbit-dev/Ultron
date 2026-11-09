import argparse
import hashlib
from pathlib import Path


def _index(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            out[str(p.relative_to(root))] = h
    return out


def run(args: argparse.Namespace) -> int:
    a, b = Path(args.a), Path(args.b)
    for path in (a, b):
        if not path.is_dir():
            print(f"not a directory: {path}")
            return 1

    ia, ib = _index(a), _index(b)
    only_a = sorted(set(ia) - set(ib))
    only_b = sorted(set(ib) - set(ia))
    modified = sorted(k for k in set(ia) & set(ib) if ia[k] != ib[k])

    print(f"only in {a}: {len(only_a)}")
    for k in only_a:
        print(f"  - {k}")
    print(f"only in {b}: {len(only_b)}")
    for k in only_b:
        print(f"  + {k}")
    print(f"modified: {len(modified)}")
    for k in modified:
        print(f"  ~ {k}")

    return 0 if not (only_a or only_b or modified) else 1


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("diffscan", help="compare two directories by path + hash")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(func=run)