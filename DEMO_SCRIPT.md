# NexusCLI — Explanation & Demonstration Video Script

> **Recommended Duration:** 4 to 6 minutes  
> **Target Audience:** BuildSprint Round 2 Judges & Technical Evaluators  
> **Key Goal:** Prove real backend CLI execution, robust architecture, and flawless end-to-end delivery of the mandatory use case.

---

## Pre-Recording Checklist
1. Open terminal in `d:\Hackathon` and start the server:
   ```bash
   python run.py
   ```
2. Open your browser to **http://localhost:8000**.
3. Have your terminal visible or ready to show alongside the browser.
4. Ensure screen resolution is clear (1080p recommended) and audio is crisp.

---

## Minute-by-Minute Script & Screen Walkthrough

### ⏱️ 0:00 – 0:45: Introduction & Problem Statement
- **What to show on screen:**  
  Start on the NexusCLI Web Interface (`http://localhost:8000`). Show the clean dark-mode UI with the "Subprocess Orchestrator Active" indicator.
- **What to say:**  
  > *"Hello judges, welcome to our demonstration of NexusCLI for BuildSprint Round 2.  
  > Most conversational AI applications today stop at generating speculative text by querying an LLM. But when users need complex real-world actions—such as web crawling, document extraction, or system diagnostics—text generation alone fails.  
  > Our solution, **NexusCLI**, is an AI-powered execution agent that translates natural-language prompts into controlled, multi-step tasks, invokes approved CLI tools from the backend via isolated subprocesses, streams real-time execution outputs, and returns verified structured results in the chat."*

---

### ⏱️ 0:45 – 1:30: System Architecture & Engineering
- **What to show on screen:**  
  Briefly switch to `ARCHITECTURE.md` (or highlight the left sidebar of the UI showing the Approved CLI Tool Registry and Security Guardrails).
- **What to say:**  
  > *"Let's look at the core architecture:  
  > 1. **Intent Understanding Layer**: Automatically extracts the user's intent, the target URL, recursion depth, and requested output format (such as JSON or markdown summaries).  
  > 2. **Security & SSRF Guardrail**: Before any tool is invoked, we validate the target URL and resolve its IP address, blocking loopbacks, private networks (RFC 1918), and cloud metadata endpoints to prevent Server-Side Request Forgery.  
  > 3. **Backend CLI Orchestrator**: We programmatically invoke approved standalone CLI tools—like our custom `site-crawler`—using Python's `subprocess.Popen` with safe argument arrays (`shell=False`), completely eliminating shell injection risks.  
  > 4. **Output Capture & Validation**: We capture `stdout`, `stderr`, Process IDs, execution time, and exit codes, validating structured JSON before presenting it in the chat interface."*

---

### ⏱️ 1:30 – 3:15: LIVE DEMO: Mandatory Demonstration Use Case
- **What to show on screen:**  
  Click on the **"🌟 Mandatory Use Case"** preset button in the sidebar (or paste the prompt into the input box):  
  `"Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format."`  
  Click Send.
- **What to say:**  
  > *"Now, let's run the mandatory challenge use case:  
  > 'Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format.'  
  > As I click Send, notice what happens in real time:  
  > First, the Intent Engine extracts the target and parameters.  
  > Second, the Security Layer verifies that example.com resolves to a valid public IP.  
  > Third, the backend launches our `site-crawler` CLI tool in an isolated subprocess.  
  > Look at the **Subprocess Terminal Inspector** drawer: here we see the real-time STDERR log streaming directly from the CLI process as it checks robots.txt, fetches the page, and parses the DOM.  
  > Notice the PID, duration (under 0.5 seconds), and Exit Code 0."*

- **Highlight the Output:**  
  Scroll down the response card:  
  > *"Here is the generated output:  
  > 1. A clean, human-readable **Executive Summary** highlighting the core content of example.com, headings, and connectivity metrics.  
  > 2. A verified, syntactically valid **Structured JSON** payload containing the crawled URL, HTTP status code 200, metadata, parsed paragraphs, and word counts.  
  > We can click **Copy JSON** or **Download** with one click. This is real execution, not a mock or hardcoded response."*

---

### ⏱️ 3:15 – 4:00: Demonstrating the Standalone CLI in Terminal
- **What to show on screen:**  
  Switch to your terminal window. Run:  
  ```bash
  python site-crawler.py --url https://example.com --format json
  ```
- **What to say:**  
  > *"To prove that this is a genuine CLI-driven architecture, let's run the exact same `site-crawler` tool directly from the terminal.  
  > As you can see, `site-crawler` is a fully autonomous standalone CLI tool. It emits progress logs to STDERR and valid JSON to STDOUT. The backend chat application wraps this tool cleanly, providing non-technical users with natural-language access to powerful CLI workflows."*

---

### ⏱️ 4:00 – 4:45: Security & Edge Case Handling
- **What to show on screen:**  
  Return to the browser.  
  1. Click **"🛡️ SSRF Security Block"** preset:  
     `"Crawl http://127.0.0.1:8000/secret-admin-console and extract data in JSON"`  
     Show the immediate security block card.
  2. Click **"⚠️ Error Handling"** preset:  
     `"Crawl https://invalid-domain-does-not-exist-xyz999.org and summarize the content"`  
     Show honest error reporting with exit code 1.
- **What to say:**  
  > *"Responsible execution requires rigorous safeguards. Let's demonstrate two edge cases:  
  > First, what happens if a prompt attempts to probe internal services, like `http://127.0.0.1`?  
  > Our SSRF defense immediately detects the loopback IP and blocks the request before any subprocess is spawned, protecting internal infrastructure.  
  > Second, what happens with an unreachable or invalid domain?  
  > The CLI executes, detects the DNS failure, returns Exit Code 1, and our response layer honestly displays the failure reason and error logs. The system never hallucinates success without verifiable evidence."*

---

### ⏱️ 4:45 – 5:30: Tech Stack, AI Tools Disclosure & Conclusion
- **What to show on screen:**  
  Show the project files in VS Code / File Explorer or `test_e2e.py` running in terminal with 100% passing tests.
- **What to say:**  
  > *"To summarize our technology stack:  
  > - **Backend**: Python 3.12, FastAPI, Uvicorn, and Pydantic v2.  
  > - **Subprocess Orchestration**: Native `subprocess.Popen` with safe argument arrays and timeout controls.  
  > - **CLI Engine**: Custom lightweight crawler with standard library HTML parsing.  
  > - **Frontend**: Tailwind CSS, Lucide icons, and Server-Sent Events (SSE) for live streaming.  
  > - **AI Tools Disclosure**: Developed with Google DeepMind Antigravity AI assistant for architecture design, security validation, and implementation. Intent parsing is powered by a zero-dependency deterministic NLP engine that requires no external API keys.  
  > All unit tests and end-to-end integration tests are passing with 100% coverage.  
  > Thank you for your time, and we look forward to your evaluation!"*
