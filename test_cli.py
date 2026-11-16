"""Automated test suite for standalone CLI tools."""
import sys
import subprocess
import json
import pytest

def test_site_crawler_help():
    """Verify site-crawler CLI responds to --help."""
    res = subprocess.run(
        [sys.executable, "site-crawler.py", "--help"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    assert "Autonomous CLI website crawler" in res.stdout
    assert "--url" in res.stdout

def test_site_crawler_invalid_url():
    """Verify site-crawler rejects invalid URL schemes."""
    res = subprocess.run(
        [sys.executable, "site-crawler.py", "--url", "invalid-scheme://example.com"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 2
    assert "Invalid URL" in res.stderr

def test_dns_inspector_tool():
    """Verify dns-inspector CLI tool runs and produces valid JSON."""
    res = subprocess.run(
        [sys.executable, "crawler/tools/dns_inspector.py", "--domain", "example.com", "--format", "json"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["domain"] == "example.com"
    assert "resolved_ips" in data
    assert data["status"] == "success"

if __name__ == "__main__":
    print("[*] Running CLI unit tests...")
    test_site_crawler_help()
    print("  ✓ site-crawler --help passed")
    test_site_crawler_invalid_url()
    print("  ✓ site-crawler invalid URL rejection passed")
    test_dns_inspector_tool()
    print("  ✓ dns-inspector tool passed")
    print("[+] All CLI unit tests passed successfully!")

