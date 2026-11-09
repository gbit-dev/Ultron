import argparse
import re
import sys
import time
from pathlib import Path


def run(args: argparse.Namespace) -> int:
    pattern = re.compile(args.pattern) if args.pattern else None
    path = Path(args.file)

    def emit(line: str) -> None:
        if pattern and not pattern.search(line):
            return
        sys.stdout.write(line if line.endswith("\n") else line + "\n")
        sys.stdout.flush()

    if not args.follow:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                emit(line)
        return 0

    with path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(0, 2)
        try:
            while True:
                line = f.readline()
                if line:
                    emit(line)
                else:
                    time.sleep(0.2)
        except KeyboardInterrupt:
            return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("logtail", help="filter and follow a log file")
    p.add_argument("file")
    p.add_argument("-p", "--pattern", help="regex filter")
    p.add_argument("-f", "--follow", action="store_true", help="follow like tail -f")
    p.set_defaults(func=run)