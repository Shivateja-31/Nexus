"""End-to-End integration test suite for NexusCLI backend API and subprocess orchestrator."""
import os
import sys
import json
from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "site-crawler" in data["approved_tools"]

def test_tools_endpoint():
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "site-crawler" in data["tools"]
    assert "dns-inspector" in data["tools"]

def test_ssrf_blocking_loopback():
    """Verify system blocks access to localhost/127.0.0.1."""
    resp = client.post("/api/chat", json={"message": "Crawl http://127.0.0.1:8000/admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["status"] == "security_blocked"
    assert "SSRF" in data["summary_markdown"]

def test_ssrf_blocking_cloud_metadata():
    """Verify system blocks access to cloud metadata IP 169.254.169.254."""
    resp = client.post("/api/chat", json={"message": "Crawl http://169.254.169.254/latest/meta-data"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["status"] == "security_blocked"

def test_mandatory_demonstration_use_case():
    """Verify mandatory prompt executes real CLI process on example.com and returns structured JSON."""
    prompt = "Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format."
    resp = client.post("/api/chat", json={"message": prompt})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["status"] == "completed"
    assert data["execution_meta"]["tool_name"] == "site-crawler"
    assert data["execution_meta"]["exit_code"] == 0
    assert data["structured_json"] is not None
    assert data["structured_json"]["target_url"] == "https://example.com"
    assert len(data["structured_json"]["pages"]) > 0
    assert "Example Domain" in data["summary_markdown"]

def test_dns_tool_invocation():
    """Verify tool selection for DNS inspection."""
    prompt = "Inspect DNS and IP records for example.com"
    resp = client.post("/api/chat", json={"message": prompt})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["execution_meta"]["tool_name"] == "dns-inspector"
    assert "resolved_ips" in data["structured_json"]

if __name__ == "__main__":
    print("[*] Running End-to-End API and Subprocess Tests...")
    test_health_endpoint()
    print("  ✓ /api/health passed")
    test_tools_endpoint()
    print("  ✓ /api/tools passed")
    test_ssrf_blocking_loopback()
    print("  ✓ SSRF Loopback protection passed")
    test_ssrf_blocking_cloud_metadata()
    print("  ✓ SSRF Cloud Metadata protection passed")
    test_mandatory_demonstration_use_case()
    print("  ✓ Mandatory use case (Crawl example.com -> CLI -> JSON) passed")
    test_dns_tool_invocation()
    print("  ✓ Secondary CLI tool (dns-inspector) passed")
    print("\n[+] ALL END-TO-END INTEGRATION TESTS PASSED (100%)!")
