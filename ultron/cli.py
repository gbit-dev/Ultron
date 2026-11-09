import argparse
import sys

from ultron import __version__

BANNER = """
\033[91m
    ██╗   ██╗██╗  ████████╗██████╗  ██████╗ ███╗   ██╗
    ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
    ██║   ██║██║     ██║   ██████╔╝██║   ██║██╔██╗ ██║
    ██║   ██║██║     ██║   ██╔══██╗██║   ██║██║╚██╗██║
    ╚██████╔╝███████╗██║   ██║  ██║╚██████╔╝██║ ╚████║
     ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
          [ S Y S T E M   O N L I N E ]
\033[0m
"""

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ultron",
        description="Ultron CLI toolbox: ip, hashscan, fetch, recon, diffscan, logtail",
    )
    p.add_argument("--version", action="version", version=f"ultron {__version__}")
    
    # required=False para permitir rodar só "ultron"
    sub = p.add_subparsers(dest="command", required=False)

    from ultron.commands import diffscan, fetch, hashscan, ip as ip_cmd, logtail, recon

    ip_cmd.register(sub)
    hashscan.register(sub)
    fetch.register(sub)
    recon.register(sub)
    diffscan.register(sub)
    logtail.register(sub)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    
    if not getattr(args, "command", None):
        print(BANNER)
        print(" type 'ultron --help' for commands.\n")
        return 0

    handler = getattr(args, "func", None)
    if handler is None:
        print("no command", file=sys.stderr)
        return 2
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
