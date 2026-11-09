import argparse
import json
import ssl
import socket
from datetime import datetime, timezone

import dns.resolver


def _dns(name: str) -> dict:
    out = {}
    for rtype in ("A", "AAAA", "MX", "TXT", "NS"):
        try:
            answers = dns.resolver.resolve(name, rtype, lifetime=5)
            out[rtype] = [str(a) for a in answers]
        except Exception:
            out[rtype] = []
    return out


def _tls(host: str, port: int = 443) -> dict:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return {
                    "issuer": dict(x[0] for x in cert.get("issuer", [])),
                    "subject": dict(x[0] for x in cert.get("subject", [])),
                    "not_after": cert.get("notAfter"),
                }
    except Exception as e:
        return {"error": str(e)}


def run(args: argparse.Namespace) -> int:
    result = {"domain": args.domain, "dns": _dns(args.domain), "tls": _tls(args.domain)}
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"domain: {args.domain}")
        for rtype, values in result["dns"].items():
            print(f"  {rtype:<4} {', '.join(values) if values else '-'}")
        tls = result["tls"]
        if "error" in tls:
            print(f"  TLS  error: {tls['error']}")
        else:
            issuer = tls["issuer"].get("organizationName", tls["issuer"].get("commonName", "?"))
            print(f"  TLS  issuer={issuer}  expires={tls['not_after']}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("recon", help="DNS + TLS info for a domain")
    p.add_argument("domain")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=run)