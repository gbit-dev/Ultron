import argparse
import json

import httpx


def run(args: argparse.Namespace) -> int:
    results = []
    with httpx.Client(follow_redirects=True, timeout=args.timeout) as client:
        for url in args.urls:
            try:
                r = client.get(url)
                title = ""
                if "text/html" in r.headers.get("content-type", ""):
                    import re
                    m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.I | re.S)
                    if m:
                        title = m.group(1).strip()
                results.append({
                    "url": url,
                    "final_url": str(r.url),
                    "status": r.status_code,
                    "content_type": r.headers.get("content-type", ""),
                    "bytes": len(r.content),
                    "title": title,
                })
            except httpx.HTTPError as e:
                results.append({"url": url, "error": str(e)})

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if "error" in r:
                print(f"{r['url']}  ERROR  {r['error']}")
            else:
                print(f"{r['status']}  {r['bytes']:>8}  {r['final_url']}  {r['title'][:60]}")
    return 0 if all("error" not in r for r in results) else 1


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("fetch", help="fetch URL metadata (status, title, size)")
    p.add_argument("urls", nargs="+", help="one or more URLs")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=run)