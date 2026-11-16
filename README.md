# NexusCLI — CLI-Driven AI Chat Execution for Complex Tasks

> **BuildSprint Round 2 Prototype Submission**  
> An AI-powered conversational application that translates natural-language instructions into controlled, multi-step CLI tool executions, captures real-time outputs, and returns verified structured results.

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests Passing](https://img.shields.io/badge/Tests-Passing%20(100%25)-emerald.svg)](#6-testing--verification)

---

## 1. Challenge & Problem Statement

Conventional AI chat applications send prompts to an LLM and return generated text without interacting with the real world. For complex real-world tasks (e.g. web crawling, data extraction, script execution, network diagnostics), systems must perform **real, verifiable work**.

**NexusCLI** solves this by:
1. **Understanding Intent**: Analyzing natural-language user requests into structured tasks.
2. **Backend CLI Execution**: Spawning approved, standalone CLI tools (`site-crawler`, `dns-inspector`) via isolated subprocesses (strictly avoiding shell injection).
3. **Real-time Output Capture**: Streaming `stdout`, `stderr`, Process IDs, and exit codes live to the user.
4. **Validation & Presentation**: Verifying structured JSON output, extracting key metrics, and synthesizing an executive markdown summary alongside an interactive terminal inspector.

---

## 2. Mandatory Demonstration Use Case

The system is configured and tested out-of-the-box for the mandatory challenge prompt:

> **"Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format."**

### How NexusCLI Executes This:
1. **Chat Input**: Accepts prompt and detects intent (target: `https://example.com`, tool: `site-crawler`, flags: `format=json`, `summary=true`).
2. **SSRF & Security Check**: Validates the URL and ensures the IP does not resolve to internal, private, or cloud metadata ranges (`127.0.0.1`, `169.254.169.254`).
3. **CLI Invocation**: Spawns `python site-crawler.py --url https://example.com --format json` in an isolated subprocess.
4. **Live Execution**: Traverses the site, checks `robots.txt`, parses HTML tags (`<title>`, `<meta>`, headings, body text, links), and emits runtime logs to `stderr`.
5. **Output Capture & Validation**: Validates the exit code (`0`) and parses `stdout` as syntactically valid JSON.
6. **Chat Presentation**: Renders an executive summary, crawl metrics, interactive JSON viewer with copy/download buttons, and an expandable **Terminal Execution Inspector**.

---

## 3. Technology Stack & Disclosure

- **Backend**: Python 3.12, FastAPI, Uvicorn, Pydantic v2
- **Process Orchestration**: `subprocess.Popen` (safe argument array, `shell=False`, timeout killswitch)
- **Crawler CLI**: Standalone Python module (`crawler/cli.py`, `site-crawler.py`, `site-crawler.bat`)
- **HTML Parsing**: Python standard library `html.parser` (zero external parsing vulnerabilities, hardened against malformed HTML)
- **Frontend**: Responsive Single-Page Application (SPA), Tailwind CSS, Lucide Icons, Server-Sent Events (SSE)
- **Testing**: `pytest`, FastAPI `TestClient`
- **AI Tools Disclosure**: Developed with Google DeepMind Antigravity AI assistant for architecture design, security validation, and rapid implementation. Built-in deterministic NLP engine handles intent understanding out of the box without requiring external LLM API tokens.

---

## 4. Quickstart Guide (Local Setup)

### Prerequisites
- Python 3.10 or higher installed (`python --version`)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/nexus-cli.git
   cd nexus-cli
   ```

2. **(Optional) Create and activate virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Application**:
   ```bash
   python run.py
   ```
   *The server starts on `http://127.0.0.1:8000`.*

5. **Open in Browser**:
   Open **[http://localhost:8000](http://localhost:8000)** to interact with the chat interface.

---

## 5. Direct CLI Usage (Standalone Tool)

The core crawler tool can also be run independently from any terminal:

```bash
# Basic single page crawl with JSON output
python site-crawler.py --url https://example.com --format json

# Multi-page crawl with depth limit
python site-crawler.py --url https://httpbin.org --max-pages 2 --max-depth 2

# Text summary output
python site-crawler.py --url https://example.com --format summary

# Save structured output to file
python site-crawler.py --url https://example.com --output-file results.json
```

### CLI Arguments Reference:
| Flag | Description | Default | Allowed Values |
|------|-------------|---------|----------------|
| `--url`, `-u` | Target website URL (*Required*) | `None` | `http://*`, `https://*` |
| `--max-pages`, `-p` | Maximum pages to traverse | `1` | `1` to `20` |
| `--max-depth`, `-d` | Maximum link depth | `1` | `1` to `3` |
| `--timeout`, `-t` | Per-page request timeout (seconds) | `15` | `5` to `60` |
| `--format`, `-f` | Output format | `json` | `json`, `summary`, `full` |
| `--output-file`, `-o` | File path to write JSON output | `None` | Valid file path |
| `--ignore-robots` | Bypass robots.txt check | `False` | Flag |

---

## 6. Testing & Verification

Run the automated test suites to verify CLI correctness, input validation, and SSRF security defenses:

```bash
# 1. Run CLI tool unit tests
python test_cli.py

# 2. Run End-to-End API and Subprocess integration tests
python test_e2e.py
```

Expected output:
```text
[*] Running End-to-End API and Subprocess Tests...
  ✓ /api/health passed
  ✓ /api/tools passed
  ✓ SSRF Loopback protection passed
  ✓ SSRF Cloud Metadata protection passed
  ✓ Mandatory use case (Crawl example.com -> CLI -> JSON) passed
  ✓ Secondary CLI tool (dns-inspector) passed

[+] ALL END-TO-END INTEGRATION TESTS PASSED (100%)!
```

---

## 7. Security Safeguards & Responsible Execution

1. **Strict Subprocess Execution (`shell=False`)**:  
   Commands are executed strictly via argument lists `[sys.executable, script_path, "--url", validated_url]`. Shell interpolation (`shell=True`) is completely disabled, preventing arbitrary shell command injection.

2. **SSRF (Server-Side Request Forgery) Defense**:  
   Before invoking the crawler, the backend resolves the target host's IP address and blocks access to:
   - Loopback addresses (`127.0.0.0/8`, `::1`)
   - Private RFC-1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   - Cloud metadata IP endpoints (`169.254.169.254`, `169.254.0.0/16`)
   - Non-routable internal hostnames (`localhost`, `metadata.google.internal`)

3. **Tool Allowlisting**:  
   Only approved CLI tools in the registry (`site-crawler`, `dns-inspector`) can be invoked. Arbitrary commands from user input or LLM generation are rejected.

4. **Resource Constraints & Timeouts**:  
   - Maximum execution timeout enforced by watchdog (default 30 seconds). If exceeded, `process.kill()` terminates the subprocess.
   - Bounded recursion depth (`max_depth <= 3`) and page ceiling (`max_pages <= 20`).
   - Rate limiting delay (`0.5s`) between HTTP requests.

5. **Honest Status Reporting**:  
   Failures (HTTP 404, DNS resolution failure, connection timeouts) are honestly surfaced with exit codes and error logs. The system never fakes or hallucinates success.

---

## 8. Demonstration Video Walkthrough Script

A complete, step-by-step 4–7 minute video recording guide with talking points and screen demonstration instructions is available in [DEMO_SCRIPT.md](file:///d:/Hackathon/DEMO_SCRIPT.md).

---

## 9. Project Directory Structure

```text
d:\Hackathon\
├── crawler/                      # Standalone CLI crawler engine
│   ├── __init__.py
│   ├── cli.py                    # Main CLI entrypoint
│   ├── engine.py                 # HTTP crawler, BFS queue, rate-limiter
│   ├── parser.py                 # HTML parser & information extractor
│   ├── models.py                 # Pydantic data schemas
│   └── tools/
│       └── dns_inspector.py      # Secondary approved CLI tool
├── backend/                      # Backend API & Orchestration
│   ├── __init__.py
│   ├── app.py                    # FastAPI server (Chat & Streaming endpoints)
│   ├── intent_engine.py          # Dual-mode AI intent analyzer
│   ├── cli_orchestrator.py       # Safe subprocess manager with output capture
│   ├── security.py               # Input validation & SSRF defense
│   └── formatter.py              # Output validator & response synthesizer
├── frontend/                     # Interactive Web Application
│   ├── index.html                # Modern chat UI layout
│   ├── app.js                    # Chat UI logic, SSE stream, terminal drawer
│   └── styles.css                # Terminal styling, dark mode theme
├── site-crawler.py               # Root executable CLI wrapper
├── site-crawler.bat              # Windows batch wrapper
├── run.py                        # Single-command server launcher
├── test_cli.py                   # Automated CLI test suite
├── test_e2e.py                   # End-to-end integration test suite
├── requirements.txt              # Project dependencies
├── ARCHITECTURE.md               # System architecture & sequence diagrams
├── DEMO_SCRIPT.md                # Video presentation script
└── README.md                     # Documentation & setup guide
```

---

## 10. Authors & Acknowledgments

- **Participant**: Team Nexus
- **Competition**: BuildSprint Round 2 (CLI-Driven AI Chat Execution for Complex Tasks)
- **Submission Date**: November 16, 2026
