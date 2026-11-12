import ast
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agent_forge.tools.base import BaseTool, SafetyLevel


class GitDiffInput(BaseModel):
    repo_path: str = Field(default=".", description="Path to git repository root")
    staged: bool = Field(default=False, description="Inspect staged changes (--cached)")


class GitDiffInspector(BaseTool):
    name = "git_diff_inspector"
    description = "Inspects unstaged or staged git diffs within a repository"
    category = "dev"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = GitDiffInput

    def execute(self, repo_path: str = ".", staged: bool = False) -> Dict[str, Any]:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        res = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "exit_code": res.returncode,
            "diff": res.stdout,
            "stderr": res.stderr,
            "is_empty": len(res.stdout.strip()) == 0,
        }


class TestRunnerInput(BaseModel):
    command: str = Field(
        default="pytest -q",
        description="Test command to execute (e.g. 'pytest -q', 'npm test')",
    )
    working_dir: str = Field(
        default=".",
        description="Directory to run tests in",
    )
    timeout_seconds: int = Field(
        default=60,
        description="Maximum execution time in seconds",
    )


class TestRunnerSandbox(BaseTool):
    name = "test_runner_sandbox"
    description = "Executes an automated test suite and reports pass/fail status and output"
    category = "dev"
    safety_level = SafetyLevel.MUTATING_SAFE
    args_schema = TestRunnerInput

    def execute(
        self,
        command: str = "pytest -q",
        working_dir: str = ".",
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
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
                "passed": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "passed": False,
                "exit_code": -1,
                "stdout": exc.stdout or "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds",
                "timed_out": True,
            }


class ASTAuditInput(BaseModel):
    file_path: str = Field(..., description="Path to Python file to statically analyze")


class ASTCodeAuditor(BaseTool):
    name = "ast_code_auditor"
    description = "Performs AST static inspection on Python files to detect syntax errors and anti-patterns"
    category = "dev"
    safety_level = SafetyLevel.READ_ONLY
    args_schema = ASTAuditInput

    def execute(self, file_path: str) -> Dict[str, Any]:
        target = Path(file_path).resolve()
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"Target file does not exist: {target}")

        code = target.read_text(encoding="utf-8")
        try:
            tree = ast.parse(code, filename=str(target))
        except SyntaxError as syn_err:
            return {
                "syntax_valid": False,
                "error": f"SyntaxError at line {syn_err.lineno}: {syn_err.msg}",
                "findings": [],
            }

        findings: List[Dict[str, Any]] = []

        class Visitor(ast.NodeVisitor):
            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                if node.type is None:
                    findings.append({
                        "line": node.lineno,
                        "rule": "no-bare-except",
                        "severity": "warning",
                        "message": "Bare 'except:' catch-all hides system exceptions like KeyboardInterrupt.",
                    })
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("breakpoint",):
                        findings.append({
                            "line": node.lineno,
                            "rule": "no-breakpoint",
                            "severity": "error",
                            "message": "Debug breakpoint() invocation left in code.",
                        })
                self.generic_visit(node)

        visitor = Visitor()
        visitor.visit(tree)

        return {
            "syntax_valid": True,
            "total_findings": len(findings),
            "findings": findings,
        }


class GitCommitInput(BaseModel):
    repo_path: str = Field(default=".", description="Path to git repository")
    message: str = Field(..., description="Conventional commit message (e.g. 'feat: add auth gate')")
    stage_all: bool = Field(default=False, description="Whether to run 'git add -A' prior to commit")


class GitCommitMaker(BaseTool):
    name = "git_commit_maker"
    description = "Creates a git commit ensuring adherence to Conventional Commits standard"
    category = "dev"
    safety_level = SafetyLevel.MUTATING_SAFE
    args_schema = GitCommitInput

    CONVENTIONAL_REGEX = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-zA-Z0-9_\-\.]+\))?: .+$"
    )

    def execute(self, repo_path: str = ".", message: str = "", stage_all: bool = False) -> Dict[str, Any]:
        msg_clean = message.strip()
        if not self.CONVENTIONAL_REGEX.match(msg_clean):
            raise ValueError(
                f"Commit message does not adhere to Conventional Commits: '{msg_clean}'. "
                "Expected prefix like 'feat:', 'fix:', 'chore:', etc."
            )

        if stage_all:
            subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)

        res = subprocess.run(
            ["git", "commit", "-m", msg_clean],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "committed": res.returncode == 0,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }
