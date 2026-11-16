"""FastAPI backend application orchestrating intent parsing, security validation, and CLI invocation."""
import os
import sys
import json
import uuid
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .security import validate_target_url, validate_cli_tool, APPROVED_CLI_TOOLS
from .intent_engine import IntentEngine, TaskIntent
from .cli_orchestrator import CLIOrchestrator, ExecutionResult
from .formatter import OutputFormatter, ChatResponse

# App setup
app = FastAPI(
    title="NexusCLI Agent API",
    description="CLI-Driven AI Chat Execution for Complex Tasks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root directory reference
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Core service singletons
intent_engine = IntentEngine()
orchestrator = CLIOrchestrator(workspace_root=BASE_DIR)

class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language prompt from user")
    allow_private_ip: bool = Field(default=False, description="For testing SSRF defenses")

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "NexusCLI-Agent",
        "version": "1.0.0",
        "approved_tools": list(APPROVED_CLI_TOOLS.keys())
    }

@app.get("/api/tools")
def list_tools():
    """Return approved CLI tools and metadata."""
    return {
        "tools": APPROVED_CLI_TOOLS,
        "security_policy": {
            "ssrf_protection": "Enabled (Blocks RFC-1918, loopbacks, and cloud metadata)",
            "execution_isolation": "Subprocess with strict argument list (No shell injection)",
            "default_timeout_seconds": 30
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
def handle_chat_message(req: ChatRequest):
    """
    Standard synchronous chat execution endpoint:
    1. Parse intent
    2. Validate inputs & SSRF
    3. Run CLI subprocess
    4. Format and return response
    """
    exec_id = str(uuid.uuid4())[:8]
    prompt = req.message.strip()

    # Step 1: Interpret user intent
    intent = intent_engine.parse(prompt)

    # Handle conversational or help queries
    if intent.intent_type == "conversational":
        return ChatResponse(
            success=True,
            status="completed",
            message="Hello! I am NexusCLI, an AI agent capable of executing complex web tasks via controlled backend CLI tools.",
            summary_markdown=(
                "### Welcome to NexusCLI!\n\n"
                "I translate your natural-language instructions into controlled CLI tasks and execute real tools from the backend.\n\n"
                "**Try one of these examples:**\n"
                "- `Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format.`\n"
                "- `Scrape https://httpbin.org with depth 2 and give me the extracted data in JSON`\n"
                "- `Inspect DNS and IP records for wikipedia.org`\n"
                "- `Crawl http://127.0.0.1:8000/internal` (Demonstrates SSRF security blocking)\n"
            ),
            structured_json=None,
            terminal_logs="No CLI execution required for conversational prompt."
        )

    if intent.intent_type == "error":
        return ChatResponse(
            success=False,
            status="invalid_input",
            message=intent.error_message or "Invalid request.",
            summary_markdown=f"> [!WARNING]\n> {intent.error_message}",
            structured_json=None,
            terminal_logs="Input validation failed before CLI invocation."
        )

    # Step 2: Validate Target URL & Enforce SSRF Safeguards
    if intent.target_url:
        is_valid, sanitized_url, resolved_ip = validate_target_url(
            intent.target_url,
            allow_private=req.allow_private_ip
        )
        if not is_valid:
            return OutputFormatter.format_security_block(sanitized_url, intent.target_url)

        # Update intent with sanitized URL
        intent.target_url = sanitized_url
        if "--url" in intent.cli_args:
            idx = intent.cli_args.index("--url")
            intent.cli_args[idx + 1] = sanitized_url

    # Step 3: Verify Tool Authorization
    if not validate_cli_tool(intent.tool_name):
        raise HTTPException(status_code=403, detail=f"CLI tool '{intent.tool_name}' is not in approved security allowlist.")

    # Step 4: Execute CLI Subprocess
    exec_result = orchestrator.execute_sync(
        execution_id=exec_id,
        tool_name=intent.tool_name,
        args=intent.cli_args,
        timeout_seconds=30
    )

    # Step 5: Format and Return Chat Response
    chat_response = OutputFormatter.format_cli_response(intent, exec_result)
    return chat_response

@app.post("/api/chat/stream")
async def handle_chat_stream(req: ChatRequest):
    """
    Streaming SSE endpoint that emits live lifecycle events as the CLI tool runs:
    - intent_parsed
    - security_passed
    - cli_started
    - cli_log (real-time stderr/stdout lines)
    - completed (final markdown & structured JSON)
    """
    exec_id = str(uuid.uuid4())[:8]
    prompt = req.message.strip()

    async def event_generator():
        # Event 1: Start
        yield f"data: {json.dumps({'event': 'start', 'message': 'Analyzing request...'})}\n\n"
        await asyncio.sleep(0.05)

        # Event 2: Intent Parsing
        intent = intent_engine.parse(prompt)
        yield f"data: {json.dumps({'event': 'intent_parsed', 'intent': intent.model_dump()})}\n\n"
        await asyncio.sleep(0.05)

        if intent.intent_type == "conversational":
            resp = ChatResponse(
                success=True,
                status="completed",
                message="Conversational response",
                summary_markdown=(
                    "### Welcome to NexusCLI!\n\n"
                    "I translate your natural-language instructions into controlled CLI tasks and execute real tools from the backend.\n\n"
                    "**Try the mandatory demo prompt:**\n"
                    "> `Crawl https://example.com, extract the important information, give me a summary, and return the extracted data in JSON format.`"
                )
            )
            yield f"data: {json.dumps({'event': 'completed', 'response': resp.model_dump()})}\n\n"
            return

        if intent.intent_type == "error":
            resp = ChatResponse(
                success=False,
                status="invalid_input",
                message=intent.error_message or "Invalid request.",
                summary_markdown=f"> [!WARNING]\n> {intent.error_message}"
            )
            yield f"data: {json.dumps({'event': 'completed', 'response': resp.model_dump()})}\n\n"
            return

        # Event 3: Security Validation
        if intent.target_url:
            is_valid, sanitized_url, resolved_ip = validate_target_url(
                intent.target_url,
                allow_private=req.allow_private_ip
            )
            if not is_valid:
                resp = OutputFormatter.format_security_block(sanitized_url, intent.target_url)
                yield f"data: {json.dumps({'event': 'security_blocked', 'response': resp.model_dump()})}\n\n"
                yield f"data: {json.dumps({'event': 'completed', 'response': resp.model_dump()})}\n\n"
                return

            intent.target_url = sanitized_url
            if "--url" in intent.cli_args:
                idx = intent.cli_args.index("--url")
                intent.cli_args[idx + 1] = sanitized_url

            yield f"data: {json.dumps({'event': 'security_passed', 'url': sanitized_url, 'resolved_ip': resolved_ip})}\n\n"

        # Event 4: CLI Launch Notification
        cmd_display = f"{intent.tool_name} {' '.join(intent.cli_args)}"
        yield f"data: {json.dumps({'event': 'cli_started', 'tool': intent.tool_name, 'command': cmd_display})}\n\n"

        # Run process with streaming queue
        loop = asyncio.get_running_loop()
        log_queue = asyncio.Queue()

        def log_cb(stream_type: str, line: str):
            asyncio.run_coroutine_threadsafe(
                log_queue.put({"stream": stream_type, "line": line}),
                loop
            )

        # Run CLI in background thread
        future = loop.run_in_executor(
            None,
            lambda: orchestrator.execute_sync(
                execution_id=exec_id,
                tool_name=intent.tool_name,
                args=intent.cli_args,
                timeout_seconds=30,
                log_callback=log_cb
            )
        )

        while not future.done() or not log_queue.empty():
            try:
                item = await asyncio.wait_for(log_queue.get(), timeout=0.1)
                yield f"data: {json.dumps({'event': 'cli_log', 'stream': item['stream'], 'line': item['line']})}\n\n"
            except asyncio.TimeoutError:
                await asyncio.sleep(0.02)

        exec_result: ExecutionResult = await future

        # Final Event: Completed
        chat_response = OutputFormatter.format_cli_response(intent, exec_result)
        yield f"data: {json.dumps({'event': 'completed', 'response': chat_response.model_dump()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Serve frontend static files
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>NexusCLI Agent Frontend is building...</h2>")

