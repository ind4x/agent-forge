from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from agent_forge.tools.base import BaseTool, SafetyLevel


class BashSandboxInput(BaseModel):
    command: str = Field(..., description="Shell command string to execute")
    working_dir: str = Field(default=".", description="Execution directory")
    timeout_seconds: int = Field(default=30, description="Max runtime in seconds")


class BashSandbox(BaseTool):
    name = "bash_sandbox"
    description = "Executes shell commands within an isolated working directory with timeout limits"
    category = "ops"
    safety_level = SafetyLevel.MUTATING_SAFE
    args_schema = BashSandboxInput

    FORBIDDEN_PATTERNS = ["rm -rf /", "mkfs", "> /dev/sda", ":(){ :|:& };:"]

    def execute(
        self,
        command: str = "",
        working_dir: str = ".",
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in command:
                raise PermissionError(f"Command rejected due to dangerous pattern: '{pattern}'")

        try:
            res = subprocess.run(
                command,
                cwd=working_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "exit_code": -1,
                "stdout": exc.stdout or "",
                "stderr": f"Command timed out after {timeout_seconds} seconds",
                "timed_out": True,
            }


class ReadFileInput(BaseModel):
    path: str = Field(..., description="Path to file to read")
    max_bytes: int = Field(default=1024 * 1024, description="Max bytes to read (default 1MB)")


class SafeFileReader(BaseTool):
    name = "safe_file_reader"
    description = "Reads content of a file with size safety limits"
    category = "ops"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = ReadFileInput

    def execute(self, path: str, max_bytes: int = 1048576) -> Dict[str, Any]:
        target = Path(path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"File not found: {target}")
        if not target.is_file():
            raise IsADirectoryError(f"Target is a directory, not a file: {target}")

        file_size = target.stat().st_size
        if file_size > max_bytes:
            raise ValueError(f"File size ({file_size} bytes) exceeds limit ({max_bytes} bytes)")

        content = target.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(target),
            "size_bytes": file_size,
            "content": content,
        }


class WriteFileInput(BaseModel):
    path: str = Field(..., description="Destination file path")
    content: str = Field(..., description="Text content to write")
    create_backup: bool = Field(default=True, description="Create .bak timestamp copy if target exists")


class SafeFileWriter(BaseTool):
    name = "safe_file_writer"
    description = "Writes content to a file with automatic timestamped backup"
    category = "ops"
    safety_level = SafetyLevel.MUTATING_SAFE
    args_schema = WriteFileInput

    def execute(self, path: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
        target = Path(path).resolve()
        backup_path: Optional[str] = None

        if target.exists() and create_backup:
            ts = int(time.time())
            backup = target.with_suffix(f"{target.suffix}.{ts}.bak")
            shutil.copy2(target, backup)
            backup_path = str(backup)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        return {
            "path": str(target),
            "bytes_written": len(content.encode("utf-8")),
            "backup_created": backup_path,
        }


class SendEmailInput(BaseModel):
    recipient: str = Field(..., description="Adresse email du destinataire")
    subject: str = Field(..., description="Objet du message")
    body: str = Field(..., description="Contenu textuel du courriel")
    cc: Optional[str] = Field(default=None, description="Adresse en copie éventuelle")


class SendClientEmailTool(BaseTool):
    name = "send_client_email"
    description = "Prépare et expédie un courriel officiel à un client ou partenaire. Action critique nécessitant obligatoirement validation humaine (HITL)."
    category = "ops"
    safety_level = SafetyLevel.CRITICAL_HITL
    args_schema = SendEmailInput

    def execute(self, recipient: str, subject: str, body: str, cc: Optional[str] = None) -> Dict[str, Any]:
        return {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "cc": cc,
            "status": "EMAIL_DISPATCHED",
            "timestamp": time.time(),
        }
