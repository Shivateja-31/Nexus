"""Security safeguards: URL validation, SSRF prevention, and command allowlisting."""
import re
import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional

# Approved CLI tools allowlist
APPROVED_CLI_TOOLS = {
    "site-crawler": {
        "description": "Autonomous website crawler and structured information extractor",
        "script": "site-crawler.py",
        "allowed_flags": ["--url", "--max-pages", "--max-depth", "--timeout", "--format", "--output-file", "--ignore-robots"]
    },
    "dns-inspector": {
        "description": "DNS and SSL security inspector for domains",
        "script": "crawler/tools/dns_inspector.py",
        "allowed_flags": ["--domain", "--format"]
    }
}

# Blocked IP networks for SSRF protection
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (AWS/GCP/Azure)
    ipaddress.ip_network("0.0.0.0/8"),         # Current network
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local Address
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-Local
]

def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP belongs to private/internal/cloud metadata subnets."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in net for net in BLOCKED_IP_NETWORKS)
    except ValueError:
        return True

def validate_target_url(url: str, allow_private: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Validate target URL format and enforce SSRF defenses.
    Returns: (is_valid, sanitized_url_or_error, resolved_ip)
    """
    if not url or not isinstance(url, str):
        return False, "Target URL must be a non-empty string.", None

    url = url.strip()

    # Ensure protocol scheme
    if not re.match(r"^https?://", url, re.IGNORECASE):
        # If user typed example.com without scheme, prepend https://
        if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$", url):
            url = f"https://{url}"
        else:
            return False, f"Invalid URL scheme: URL must start with http:// or https://. Received '{url}'.", None

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Failed to parse URL: {str(e)}", None

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid URL: missing valid hostname.", None

    # Check for localhost / numeric loopback names
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
        if not allow_private:
            return False, f"Security Block (SSRF): Access to internal/loopback host '{hostname}' is restricted.", None

    # Resolve IP and verify SSRF protection
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        ips = [ai[4][0] for ai in addr_info]
        if not ips:
            return False, f"DNS Resolution failed for host '{hostname}'.", None

        primary_ip = ips[0]
        if not allow_private and is_ip_blocked(primary_ip):
            return False, f"Security Block (SSRF): Host '{hostname}' resolves to restricted internal IP {primary_ip}.", primary_ip

        return True, url, primary_ip
    except socket.gaierror:
        # DNS failed, but keep URL so crawler can report honest unreachable status
        return True, url, None
    except Exception as e:
        return False, f"URL validation error: {str(e)}", None

def validate_cli_tool(tool_name: str) -> bool:
    """Ensure tool is on the approved allowlist."""
    return tool_name in APPROVED_CLI_TOOLS
