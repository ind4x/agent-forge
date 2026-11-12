from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
import yaml

from agent_forge.models.manifest import CompanyManifest
from agent_forge.compiler.generator import DeploymentCompiler
from agent_forge.tools import create_default_registry

app = typer.Typer(
    name="agent-forge",
    help="Enterprise Multi-Agent Architecture Scaffolding and Compilation Engine",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    target_dir: Path = typer.Argument(
        Path("./manifest"),
        help="Directory to initialize the company manifest in",
    ),
    company_name: str = typer.Option(
        "Acme Enterprise",
        "--name",
        "-n",
        help="Company legal or trade name",
    ),
    slug: str = typer.Option(
        "acme-enterprise",
        "--slug",
        "-s",
        help="URL/directory safe identifier",
    ),
) -> None:
    """Scaffolds a clean reference manifest directory ready for company customization."""
    target = target_dir.resolve()
    if target.exists() and any(target.iterdir()):
        console.print(f"[bold red]Error:[/bold red] Target directory is not empty: {target}")
        raise typer.Exit(code=1)

    target.mkdir(parents=True, exist_ok=True)
    (target / "workflows").mkdir(exist_ok=True)
    (target / "policies" / "dev").mkdir(parents=True, exist_ok=True)
    (target / "policies" / "finance").mkdir(parents=True, exist_ok=True)

    # 1. company.yaml
    company_yaml = f"""name: "{company_name}"
slug: "{slug}"
domain: "agents.{slug}.internal"
timezone: "Europe/Paris"
hitl_channel: "telegram"
hitl_default_approver: "tech_lead"
thresholds:
  max_autonomous_refund_eur: 50.00
  payout_approval_threshold_eur: 1000.00
"""
    (target / "company.yaml").write_text(company_yaml.strip() + "\n", encoding="utf-8")

    # 2. org_matrix.yaml
    org_yaml = """roles:
  developer:
    name: "Developer"
    description: "Software engineer responsible for writing code and running tests"
    can_trigger:
      - "git_diff_inspector"
      - "test_runner_sandbox"
      - "ast_code_auditor"
      - "git_commit_maker"
    forbidden:
      - "deploy_production"
      - "execute_vendor_payout"

  tech_lead:
    name: "Tech Lead"
    description: "Lead architect with authorization to approve production releases"
    can_trigger:
      - "*"
    forbidden: []

  finance_lead:
    name: "Finance Lead"
    description: "Accountant responsible for invoices and banking payouts"
    can_trigger:
      - "reconcile_invoices"
      - "execute_vendor_payout"
    forbidden:
      - "deploy_production"
    spending_limit: 10000.00

segregation_of_duties:
  - action: "deploy_production"
    creator_cannot_approve: true
    required_approvers:
      - "tech_lead"
  - action: "execute_vendor_payout"
    creator_cannot_approve: true
    required_approvers:
      - "finance_lead"
"""
    (target / "org_matrix.yaml").write_text(org_yaml.strip() + "\n", encoding="utf-8")

    # 3. data_sources.yaml
    ds_yaml = """entities:
  git_repository:
    entity_name: "git_repository"
    source_of_truth: "github_enterprise"
    secondary_reads:
      - "local_mirror"
    write_policy: "strict_api_only"
    conflict_resolution: "source_wins"

  invoices:
    entity_name: "invoices"
    source_of_truth: "postgresql_ledger"
    secondary_reads: []
    write_policy: "append_only"
    conflict_resolution: "source_wins"
"""
    (target / "data_sources.yaml").write_text(ds_yaml.strip() + "\n", encoding="utf-8")

    # 4. connectors.yaml
    connectors_yaml = """connectors:
  github:
    name: "github"
    auth_type: "bearer_token"
    rate_limit_per_minute: 80
    required_env_vars:
      - "GITHUB_TOKEN"
    endpoints:
      api_url: "https://api.github.com"

  telegram_bot:
    name: "telegram_bot"
    auth_type: "api_key"
    rate_limit_per_minute: 30
    required_env_vars:
      - "TELEGRAM_BOT_TOKEN"
      - "TELEGRAM_ADMIN_CHAT_ID"
    endpoints:
      webhook_url: "https://api.telegram.org"
"""
    (target / "connectors.yaml").write_text(connectors_yaml.strip() + "\n", encoding="utf-8")

    # 5. workflows/pull_request_delivery.yaml
    pr_workflow_yaml = """name: "pull_request_delivery"
description: "End-to-end automation of code audit, test suite pass, peer review pause, and deployment"
timeout_hours: 48.0
initial_state: "verify_code"
states:
  verify_code:
    name: "verify_code"
    state_type: "autonomous"
    on_entry_tool: "test_runner_sandbox"
    transitions:
      - condition: "tests_passed"
        target: "awaiting_approval"
      - condition: "tests_failed"
        target: "verification_failed"

  awaiting_approval:
    name: "awaiting_approval"
    state_type: "human_pause"
    on_entry_tool: "deploy_production"
    timeout_hours: 24.0
    on_timeout_target: "verification_failed"
    resume_on_event: "hitl_approval_received"
    transitions:
      - condition: "approved"
        target: "deployed"
      - condition: "rejected"
        target: "verification_failed"

  deployed:
    name: "deployed"
    state_type: "terminal"
    transitions: []

  verification_failed:
    name: "verification_failed"
    state_type: "terminal"
    transitions: []
"""
    (target / "workflows" / "pull_request_delivery.yaml").write_text(
        pr_workflow_yaml.strip() + "\n", encoding="utf-8"
    )

    # 6. Sample Policies
    (target / "policies" / "dev" / "commit_guidelines.md").write_text(
        "# Conventional Commit Guidelines\nAll commits must follow Conventional Commits standard.\n",
        encoding="utf-8",
    )
    (target / "policies" / "finance" / "approval_limits.md").write_text(
        "# Financial Approvals\nAny transaction over 1,000 EUR requires explicit confirmation.\n",
        encoding="utf-8",
    )

    console.print(f"[bold green]Initialized manifest at:[/bold green] {target}")


@app.command()
def validate(
    manifest_dir: Path = typer.Argument(
        ...,
        help="Path to company manifest directory",
    ),
) -> None:
    """Validates manifest integrity, Pydantic schemas, and cross-references."""
    try:
        manifest = CompanyManifest.load_from_directory(manifest_dir)
        console.print(f"[bold green]Manifest is valid for:[/bold green] {manifest.company.name} ({manifest.company.slug})")

        table = Table(title="Manifest Overview")
        table.add_column("Layer", style="cyan")
        table.add_column("Details", style="magenta")

        table.add_row("Company", f"{manifest.company.name} | Timezone: {manifest.company.timezone} | Approver: {manifest.company.hitl_default_approver}")
        table.add_row("Roles Defined", ", ".join(manifest.org.roles.keys()))
        table.add_row("SoD Rules", f"{len(manifest.org.segregation_of_duties)} dual-control rules active")
        table.add_row("Entities Mapped", ", ".join(manifest.data_sources.entities.keys()))
        table.add_row("Workflows", ", ".join(manifest.workflows.keys()))
        table.add_row("Connectors", ", ".join(manifest.connectors.connectors.keys()))
        table.add_row("Policies", f"{len(manifest.policies)} documents ingested")

        console.print(table)
    except Exception as exc:
        console.print(f"[bold red]Validation Error:[/bold red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def build(
    manifest_dir: Path = typer.Argument(
        ...,
        help="Path to company manifest directory",
    ),
    output_dir: Path = typer.Option(
        Path("./dist"),
        "--output",
        "-o",
        help="Target directory for compiled deployment",
    ),
) -> None:
    """Compiles a company manifest into a complete, containerized LangGraph deployment."""
    try:
        manifest = CompanyManifest.load_from_directory(manifest_dir)
        compiler = DeploymentCompiler(manifest)
        out = compiler.compile(output_dir)
        console.print(f"[bold green]Successfully compiled deployment for '{manifest.company.name}' to:[/bold green] {out}")
    except Exception as exc:
        console.print(f"[bold red]Build Error:[/bold red] {exc}")
        raise typer.Exit(code=1)


@app.command("list-tools")
def list_tools() -> None:
    """Lists built-in tool packs with safety tiers."""
    registry = create_default_registry()
    table = Table(title="Agent-Forge Default Tool Fabric")
    table.add_column("Tool Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Safety Level", style="magenta")
    table.add_column("Description")

    for tool in registry.list_all():
        table.add_row(
            tool.name,
            tool.category,
            tool.safety_level.value,
            tool.description,
        )

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
