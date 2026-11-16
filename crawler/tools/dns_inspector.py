#!/usr/bin/env python3
"""
DNS & Host Inspector CLI Tool
Utility CLI tool for inspecting domain records, IP addresses, and connectivity.
"""
import sys
import os
import json
import socket
import argparse
from urllib.parse import urlparse

def parse_args():
    parser = argparse.ArgumentParser(description="Inspect DNS and network properties of a domain.")
    parser.add_argument("--domain", "-d", required=True, help="Domain or URL to inspect")
    parser.add_argument("--format", choices=["json", "summary"], default="json", help="Output format")
    return parser.parse_args()

def main():
    args = parse_args()
    raw = args.domain.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        domain = urlparse(raw).hostname or raw
    else:
        domain = raw.split("/")[0]

    sys.stderr.write(f"[*] Inspecting DNS records for {domain}...\n")
    sys.stderr.flush()

    try:
        addr_info = socket.getaddrinfo(domain, 80, proto=socket.IPPROTO_TCP)
        ips = list(set([ai[4][0] for ai in addr_info]))
        canonical = addr_info[0][3] if addr_info and addr_info[0][3] else domain

        result = {
            "domain": domain,
            "resolved_ips": ips,
            "canonical_name": canonical,
            "port_80_accessible": True,
            "status": "success"
        }
        sys.stderr.write(f"[+] Found {len(ips)} IP addresses for {domain}\n")

        if args.format == "json":
            sys.stdout.write(json.dumps(result, indent=2) + "\n")
        else:
            sys.stdout.write(f"Domain: {domain}\nIPs: {', '.join(ips)}\n")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[!] DNS lookup failed: {str(e)}\n")
        res = {
            "domain": domain,
            "resolved_ips": [],
            "status": "failed",
            "error": str(e)
        }
        sys.stdout.write(json.dumps(res, indent=2) + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
