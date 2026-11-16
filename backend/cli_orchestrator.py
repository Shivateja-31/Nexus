"""CLI Orchestration layer: Spawns approved CLI processes, captures output, and monitors execution."""
import os
import sys
import time
import queue
import threading
import subprocess
from typing import List, Dict, Any, Optional, Callable, Tuple
from pydantic import BaseModel, Field

from .security import APPROVED_CLI_TOOLS

class ExecutionResult(BaseModel):
    execution_id: str
    tool_name: str
    command_line: str
    command_args: List[str]
    pid: Optional[int] = None
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    execution_time_seconds: float = 0.0
    timed_out: bool = False
    success: bool = False
    error_message: Optional[str] = None

class CLIOrchestrator:
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.active_processes: Dict[str, subprocess.Popen] = {}

    def _resolve_tool_command(self, tool_name: str, args: List[str]) -> Tuple[List[str], str]:
        """Resolve approved tool to an absolute executable path and safe argument list."""
        if tool_name not in APPROVED_CLI_TOOLS:
            raise ValueError(f"Unauthorized CLI tool '{tool_name}'. Not in security allowlist.")

        tool_meta = APPROVED_CLI_TOOLS[tool_name]
        script_rel = tool_meta["script"]
        script_abs = os.path.normpath(os.path.join(self.workspace_root, script_rel))

        if not os.path.exists(script_abs):
            raise FileNotFoundError(f"CLI script not found at expected path: {script_abs}")

        # Execute via current Python interpreter safely without shell
        full_cmd = [sys.executable, script_abs] + args
        display_cmd = f"python {script_rel} {' '.join(args)}"
        return full_cmd, display_cmd

    def execute_sync(
        self,
        execution_id: str,
        tool_name: str,
        args: List[str],
        timeout_seconds: int = 30,
        log_callback: Optional[Callable[[str, str], None]] = None
    ) -> ExecutionResult:
        """
        Synchronously invoke approved CLI tool in isolated subprocess.
        Streams stdout and stderr via log_callback if provided.
        """
        start_time = time.time()
        try:
            full_cmd, display_cmd = self._resolve_tool_command(tool_name, args)
        except Exception as e:
            return ExecutionResult(
                execution_id=execution_id,
                tool_name=tool_name,
                command_line=f"{tool_name} {' '.join(args)}",
                command_args=args,
                exit_code=1,
                success=False,
                error_message=str(e),
                execution_time_seconds=0.0
            )

        stdout_lines = []
        stderr_lines = []
        timed_out = False

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            # Start process without shell to prevent injection
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.workspace_root,
                env=env
            )
            self.active_processes[execution_id] = process
            pid = process.pid

            # Helper to stream output
            def stream_reader(pipe, is_stderr: bool):
                try:
                    for line in iter(pipe.readline, ''):
                        if not line:
                            break
                        if is_stderr:
                            stderr_lines.append(line)
                            if log_callback:
                                log_callback("stderr", line)
                        else:
                            stdout_lines.append(line)
                            if log_callback:
                                log_callback("stdout", line)
                finally:
                    pipe.close()

            t_stdout = threading.Thread(target=stream_reader, args=(process.stdout, False))
            t_stderr = threading.Thread(target=stream_reader, args=(process.stderr, True))
            t_stdout.daemon = True
            t_stderr.daemon = True
            t_stdout.start()
            t_stderr.start()

            # Wait for completion with timeout
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()

            t_stdout.join(timeout=1.0)
            t_stderr.join(timeout=1.0)

            duration = round(time.time() - start_time, 3)
            exit_code = process.returncode if not timed_out else -9
            stdout_text = "".join(stdout_lines)
            stderr_text = "".join(stderr_lines)

            is_success = (exit_code == 0) and not timed_out
            error_msg = None
            if timed_out:
                error_msg = f"Execution timed out after {timeout_seconds} seconds."
            elif exit_code != 0:
                error_msg = f"CLI process exited with non-zero code {exit_code}."

            return ExecutionResult(
                execution_id=execution_id,
                tool_name=tool_name,
                command_line=display_cmd,
                command_args=args,
                pid=pid,
                exit_code=exit_code,
                stdout=stdout_text,
                stderr=stderr_text,
                execution_time_seconds=duration,
                timed_out=timed_out,
                success=is_success,
                error_message=error_msg
            )

        except Exception as e:
            duration = round(time.time() - start_time, 3)
            return ExecutionResult(
                execution_id=execution_id,
                tool_name=tool_name,
                command_line=display_cmd,
                command_args=args,
                exit_code=1,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines) + f"\n[Backend Exception] {str(e)}",
                execution_time_seconds=duration,
                timed_out=False,
                success=False,
                error_message=f"Process launch failure: {str(e)}"
            )
        finally:
            if execution_id in self.active_processes:
                del self.active_processes[execution_id]

    def cancel_task(self, execution_id: str) -> bool:
        """Cancel an ongoing process if running."""
        proc = self.active_processes.get(execution_id)
        if proc and proc.poll() is None:
            proc.kill()
            return True
        return False

# Small type alias helper
Tuple_Resolved = tuple[List[str], str]
