import argparse
import ipaddress
import json
import socket
import urllib.request


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _resolve(host: str) -> str:
    return socket.gethostbyname(host)


def _lookup(ip: str) -> dict:
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    with urllib.request.urlopen(url, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    if data.get("status") != "success":
        return {"error": data.get("message", "lookup failed")}
    return {
        "ip": data.get("query", ip),
        "country": data.get("country", ""),
        "country_code": data.get("countryCode", ""),
        "region": data.get("regionName", ""),
        "city": data.get("city", ""),
        "zip": data.get("zip", ""),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "timezone": data.get("timezone", ""),
        "isp": data.get("isp", ""),
        "org": data.get("org", ""),
        "asn": data.get("as", ""),
    }


def _reverse(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def _blacklist(ip: str) -> list[str]:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return []
    if addr.version != 4:
        return []
    rev = ".".join(reversed(str(addr).split(".")))
    zones = {
        "zen.spamhaus.org": "Spamhaus ZEN",
        "b.barracudacentral.org": "Barracuda",
        "bl.spamcop.net": "SpamCop",
    }
    hits = []
    for zone, label in zones.items():
        try:
            socket.gethostbyname(f"{rev}.{zone}")
            hits.append(label)
        except Exception:
            pass
    return hits


def run(args: argparse.Namespace) -> int:
    target = args.target
    ip = target if _is_ip(target) else _resolve(target)

    info = _lookup(ip)
    if "error" in info:
        print(f"erro: {info['error']}")
        return 1

    info["reverse"] = _reverse(ip)
    info["blacklist"] = _blacklist(ip)
    info["input"] = target

    if args.json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return 0

    print(f"alvo:      {target}" + ("" if target == ip else f"  ->  {ip}"))
    print(f"país:      {info['country']} ({info['country_code']})")
    print(f"região:    {info['region']}")
    print(f"cidade:    {info['city']}")
    print(f"cep:       {info['zip'] or '-'}")
    print(f"coords:    {info['lat']}, {info['lon']}")
    print(f"timezone:  {info['timezone']}")
    print(f"isp:       {info['isp']}")
    print(f"org:       {info['org']}")
    print(f"asn:       {info['asn']}")
    print(f"reverse:   {info['reverse'] or '-'}")
    print(f"blacklist: {', '.join(info['blacklist']) if info['blacklist'] else 'limpo'}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("ip", help="geolocate an IP or domain + ASN, reverse, blacklist")
    p.add_argument("target", help="IP or domain")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=run)
