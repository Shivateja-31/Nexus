"""Response Formatter: Validates CLI output and constructs clear chat responses."""
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from .cli_orchestrator import ExecutionResult
from .intent_engine import TaskIntent

class ChatResponse(BaseModel):
    success: bool
    status: str
    message: str
    summary_markdown: str = ""
    structured_json: Optional[Dict[str, Any]] = None
    execution_meta: Dict[str, Any] = Field(default_factory=dict)
    terminal_logs: str = ""
    error_details: Optional[str] = None

class OutputFormatter:
    @staticmethod
    def format_cli_response(intent: TaskIntent, exec_result: ExecutionResult) -> ChatResponse:
        terminal_logs = (
            f"$ {exec_result.command_line}\n"
            f"[PID: {exec_result.pid or 'N/A'}] [Exit Code: {exec_result.exit_code}] [Duration: {exec_result.execution_time_seconds}s]\n\n"
            f"--- STDERR ---\n{exec_result.stderr.strip() or '(no stderr output)'}\n\n"
            f"--- STDOUT ---\n{exec_result.stdout.strip() or '(no stdout output)'}"
        )

        exec_meta = {
            "tool_name": exec_result.tool_name,
            "command": exec_result.command_line,
            "pid": exec_result.pid,
            "exit_code": exec_result.exit_code,
            "duration_seconds": exec_result.execution_time_seconds,
            "timed_out": exec_result.timed_out,
            "status": "success" if exec_result.success else "failure"
        }

        # Case 1: Execution failure / timeout
        if not exec_result.success or exec_result.exit_code != 0:
            error_reason = exec_result.error_message or "Process exited with non-zero status."
            
            # Check if stdout contains partial JSON error
            parsed_json = None
            if exec_result.stdout.strip():
                try:
                    parsed_json = json.loads(exec_result.stdout)
                    if isinstance(parsed_json, dict) and "error" in parsed_json and parsed_json["error"]:
                        error_reason = parsed_json["error"]
                except Exception:
                    pass

            error_markdown = (
                f"### Task Execution Failed\n\n"
                f"The CLI tool `{exec_result.tool_name}` was invoked but encountered an error:\n\n"
                f"> **Failure Reason:** {error_reason}\n\n"
                f"- **Process Exit Code:** `{exec_result.exit_code}`\n"
                f"- **Duration:** `{exec_result.execution_time_seconds}s`\n"
                f"- **CLI Command:** `{exec_result.command_line}`\n\n"
                f"You can review the full process execution trace in the **Terminal Inspector** drawer below."
            )

            return ChatResponse(
                success=False,
                status="failure",
                message=f"Task execution failed: {error_reason}",
                summary_markdown=error_markdown,
                structured_json=parsed_json,
                execution_meta=exec_meta,
                terminal_logs=terminal_logs,
                error_details=error_reason
            )

        # Case 2: Successful Execution - Attempt JSON parsing
        parsed_json = None
        parse_error = None
        if exec_result.stdout.strip():
            try:
                parsed_json = json.loads(exec_result.stdout)
            except Exception as e:
                parse_error = f"Failed to parse CLI output as valid JSON: {str(e)}"

        # If user asked for dns-inspector tool
        if exec_result.tool_name == "dns-inspector":
            ips = parsed_json.get("resolved_ips", []) if parsed_json else []
            domain = parsed_json.get("domain", "") if parsed_json else intent.target_url
            summary_md = (
                f"### DNS Inspection Results for `{domain}`\n\n"
                f"- **Domain Name:** `{domain}`\n"
                f"- **Resolved IP Addresses:** {', '.join([f'`{ip}`' for ip in ips]) if ips else 'None'}\n"
                f"- **Port 80 Accessible:** {'Yes' if parsed_json and parsed_json.get('port_80_accessible') else 'Unknown'}\n"
                f"- **Status:** Verified Live via CLI\n"
            )
            return ChatResponse(
                success=True,
                status="completed",
                message=f"Successfully inspected DNS for {domain}.",
                summary_markdown=summary_md,
                structured_json=parsed_json,
                execution_meta=exec_meta,
                terminal_logs=terminal_logs
            )

        # Case 3: Site Crawler Result
        if parsed_json and isinstance(parsed_json, dict):
            executive_summary = parsed_json.get("executive_summary", "")
            pages_crawled = parsed_json.get("pages_crawled", 0)
            total_links = parsed_json.get("total_links_found", 0)
            target_url = parsed_json.get("target_url", intent.target_url)

            # Build markdown response combining executive summary, metrics, and data preview
            summary_blocks = []
            if executive_summary:
                summary_blocks.append(executive_summary)
            else:
                summary_blocks.append(f"### Website Content Extracted for `{target_url}`")

            # Metrics Badge Block
            metrics_block = (
                f"\n\n---\n"
                f"**Crawl Execution Metrics:**\n"
                f"- **Target URL:** {target_url}\n"
                f"- **Pages Processed:** `{pages_crawled}`\n"
                f"- **Total Links Discovered:** `{total_links}`\n"
                f"- **CLI Process Duration:** `{exec_result.execution_time_seconds}s` (PID: `{exec_result.pid}`)\n"
                f"- **Exit Code:** `0` (Success)"
            )
            summary_blocks.append(metrics_block)

            full_markdown = "".join(summary_blocks)

            return ChatResponse(
                success=True,
                status="completed",
                message=f"Successfully crawled {target_url} and extracted structured data.",
                summary_markdown=full_markdown,
                structured_json=parsed_json if intent.requires_json else None,
                execution_meta=exec_meta,
                terminal_logs=terminal_logs
            )

        # Fallback if raw text output
        return ChatResponse(
            success=True,
            status="completed",
            message="CLI task completed successfully.",
            summary_markdown=exec_result.stdout or "Task finished with no text output.",
            structured_json=None,
            execution_meta=exec_meta,
            terminal_logs=terminal_logs
        )

    @staticmethod
    def format_security_block(error_message: str, url: str) -> ChatResponse:
        """Create honest security block response."""
        md = (
            f"### Security Policy Enforcement (SSRF Prevention)\n\n"
            f"> **Execution Blocked:** {error_message}\n\n"
            f"**Why was this blocked?**\n"
            f"The application enforces strict security controls to prevent Server-Side Request Forgery (SSRF) "
            f"and unauthorized probing of internal network endpoints (e.g. localhost, loopback, private RFC-1918 subnets, "
            f"or cloud metadata addresses like `169.254.169.254`).\n\n"
            f"To test the crawler, please provide a valid public URL such as `https://example.com` or `https://httpbin.org`."
        )
        return ChatResponse(
            success=False,
            status="security_blocked",
            message=error_message,
            summary_markdown=md,
            structured_json={"error": "security_violation", "details": error_message, "url": url},
            execution_meta={"status": "blocked_by_security_policy"},
            terminal_logs=f"[SECURITY ALERT] Target '{url}' violated security policy: {error_message}"
        )
