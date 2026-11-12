from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
import yaml


class HITLChannel(str, Enum):
    TELEGRAM = "telegram"
    SLACK = "slack"
    WEBHOOK = "webhook"
    EMAIL = "email"


class CompanySpec(BaseModel):
    name: str = Field(..., description="Legal or operating name of the enterprise")
    slug: str = Field(..., description="Unique URL/directory-safe identifier")
    domain: str = Field(..., description="Internal or external fully qualified domain name")
    timezone: str = Field(default="UTC", description="Operational timezone")
    hitl_channel: HITLChannel = Field(
        default=HITLChannel.TELEGRAM,
        description="Primary channel for Human-in-the-Loop notifications and approvals",
    )
    hitl_default_approver: str = Field(
        default="admin",
        description="Identifier of default authority for escalations (e.g. 'ceo', 'lead_dev')",
    )
    thresholds: Dict[str, float] = Field(
        default_factory=dict,
        description="Autonomous execution thresholds (e.g. max_refund_eur: 50.0)",
    )


class RoleDefinition(BaseModel):
    name: str = Field(..., description="Role title (e.g. 'developer', 'finance_lead')")
    description: str = Field(..., description="Responsibilities and scope")
    can_trigger: List[str] = Field(
        default_factory=list,
        description="Tool or action names this role is explicitly allowed to execute",
    )
    forbidden: List[str] = Field(
        default_factory=list,
        description="Tool or action names strictly prohibited for this role",
    )
    spending_limit: Optional[float] = Field(
        default=None,
        description="Monetary limit in company base currency before mandatory escalation",
    )


class SegregationOfDutiesRule(BaseModel):
    action: str = Field(..., description="Sensitive action requiring dual-control")
    creator_cannot_approve: bool = Field(
        default=True,
        description="Enforces Four-Eyes Principle: origin author cannot approve their own action",
    )
    required_approvers: List[str] = Field(
        default_factory=list,
        description="List of role names authorized to sign off on this action",
    )


class OrgMatrix(BaseModel):
    roles: Dict[str, RoleDefinition] = Field(
        default_factory=dict,
        description="Dictionary mapping role identifier to role definition",
    )
    segregation_of_duties: List[SegregationOfDutiesRule] = Field(
        default_factory=list,
        description="Rules enforcing dual-control and authority limits",
    )


class EntitySource(BaseModel):
    entity_name: str = Field(..., description="Business entity name (e.g. 'customer', 'git_repo')")
    source_of_truth: str = Field(
        ...,
        description="Authoritative master system (e.g. 'hubspot', 'github_enterprise', 'postgres')",
    )
    secondary_reads: List[str] = Field(
        default_factory=list,
        description="Allowed read replicas or cached read targets",
    )
    write_policy: str = Field(
        default="strict_api_only",
        description="Policy governing mutations ('strict_api_only', 'dual_write_checked', 'append_only')",
    )
    conflict_resolution: str = Field(
        default="source_wins",
        description="Rule applied when data discrepancies arise ('source_wins', 'latest_timestamp', 'manual_audit')",
    )


class DataSourceMap(BaseModel):
    entities: Dict[str, EntitySource] = Field(
        default_factory=dict,
        description="Mapping of business entities to authoritative sources of record",
    )


class WorkflowTransition(BaseModel):
    condition: str = Field(..., description="Condition expression triggering transition")
    target: str = Field(..., description="Target state identifier")


class WorkflowStateType(str, Enum):
    AUTONOMOUS = "autonomous"
    HUMAN_PAUSE = "human_pause"
    TERMINAL = "terminal"


class WorkflowState(BaseModel):
    name: str = Field(..., description="State identifier")
    state_type: WorkflowStateType = Field(
        default=WorkflowStateType.AUTONOMOUS,
        description="Execution mode of the state",
    )
    on_entry_tool: Optional[str] = Field(
        default=None,
        description="Tool name to execute automatically upon entering this state",
    )
    timeout_hours: Optional[float] = Field(
        default=None,
        description="Maximum time allowed in this state before timeout trigger",
    )
    on_timeout_target: Optional[str] = Field(
        default=None,
        description="Target state if timeout occurs",
    )
    resume_on_event: Optional[str] = Field(
        default=None,
        description="External event schema required to unfreeze human_pause",
    )
    transitions: List[WorkflowTransition] = Field(
        default_factory=list,
        description="List of conditional transitions to subsequent states",
    )


class WorkflowSaga(BaseModel):
    name: str = Field(..., description="Unique workflow saga name")
    description: str = Field(..., description="Business purpose of this saga")
    timeout_hours: float = Field(default=72.0, description="Overall saga SLA in hours")
    initial_state: str = Field(..., description="Starting state identifier")
    states: Dict[str, WorkflowState] = Field(
        ...,
        description="All states constituting this workflow saga",
    )

    @model_validator(mode="after")
    def validate_workflow_integrity(self) -> "WorkflowSaga":
        if self.initial_state not in self.states:
            raise ValueError(
                f"Initial state '{self.initial_state}' is not defined in workflow '{self.name}' states."
            )
        for state_name, state in self.states.items():
            for transition in state.transitions:
                if transition.target not in self.states:
                    raise ValueError(
                        f"State '{state_name}' transitions to undefined state '{transition.target}'."
                    )
            if state.on_timeout_target and state.on_timeout_target not in self.states:
                raise ValueError(
                    f"State '{state_name}' on_timeout_target points to undefined state '{state.on_timeout_target}'."
                )
        return self


class ConnectorDefinition(BaseModel):
    name: str = Field(..., description="Connector identifier (e.g. 'github', 'slack', 'stripe')")
    auth_type: str = Field(
        default="bearer_token",
        description="Authentication mechanism ('bearer_token', 'basic', 'oauth2', 'api_key')",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum outbound requests allowed per minute",
    )
    required_env_vars: List[str] = Field(
        default_factory=list,
        description="Environment variable names required for authentication",
    )
    endpoints: Dict[str, str] = Field(
        default_factory=dict,
        description="Service endpoints and URLs",
    )


class ConnectorsConfig(BaseModel):
    connectors: Dict[str, ConnectorDefinition] = Field(
        default_factory=dict,
        description="Configured third-party service connectors",
    )


class CompanyManifest(BaseModel):
    company: CompanySpec
    org: OrgMatrix
    data_sources: DataSourceMap
    workflows: Dict[str, WorkflowSaga]
    connectors: ConnectorsConfig
    policies: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of policy document path to raw markdown content",
    )

    @classmethod
    def load_from_directory(cls, directory_path: Path) -> "CompanyManifest":
        """Loads and parses all 5 manifest artifacts from a standardized directory structure."""
        dir_path = Path(directory_path).resolve()
        if not dir_path.is_dir():
            raise FileNotFoundError(f"Manifest directory not found: {dir_path}")

        company_file = dir_path / "company.yaml"
        if not company_file.exists():
            raise FileNotFoundError(f"Missing required manifest file: {company_file}")
        with open(company_file, "r", encoding="utf-8") as f:
            company_data = yaml.safe_load(f) or {}
        company = CompanySpec(**company_data)

        org_file = dir_path / "org_matrix.yaml"
        if not org_file.exists():
            raise FileNotFoundError(f"Missing required manifest file: {org_file}")
        with open(org_file, "r", encoding="utf-8") as f:
            org_data = yaml.safe_load(f) or {}
        org = OrgMatrix(**org_data)

        ds_file = dir_path / "data_sources.yaml"
        if not ds_file.exists():
            raise FileNotFoundError(f"Missing required manifest file: {ds_file}")
        with open(ds_file, "r", encoding="utf-8") as f:
            ds_data = yaml.safe_load(f) or {}
        data_sources = DataSourceMap(**ds_data)

        connectors_file = dir_path / "connectors.yaml"
        if not connectors_file.exists():
            raise FileNotFoundError(f"Missing required manifest file: {connectors_file}")
        with open(connectors_file, "r", encoding="utf-8") as f:
            connectors_data = yaml.safe_load(f) or {}
        connectors = ConnectorsConfig(**connectors_data)

        workflows: Dict[str, WorkflowSaga] = {}
        workflows_dir = dir_path / "workflows"
        if workflows_dir.is_dir():
            for wf_file in workflows_dir.glob("*.yaml"):
                with open(wf_file, "r", encoding="utf-8") as f:
                    wf_data = yaml.safe_load(f) or {}
                saga = WorkflowSaga(**wf_data)
                workflows[saga.name] = saga

        policies: Dict[str, str] = {}
        policies_dir = dir_path / "policies"
        if policies_dir.is_dir():
            for policy_file in policies_dir.rglob("*.md"):
                rel_path = policy_file.relative_to(policies_dir).as_posix()
                with open(policy_file, "r", encoding="utf-8") as f:
                    policies[rel_path] = f.read()

        manifest = cls(
            company=company,
            org=org,
            data_sources=data_sources,
            workflows=workflows,
            connectors=connectors,
            policies=policies,
        )
        manifest.verify_cross_references()
        return manifest

    def verify_cross_references(self) -> None:
        """Verifies semantic coherence across distinct manifest layers."""
        # Ensure approvers in SoD exist in roles
        for rule in self.org.segregation_of_duties:
            for approver in rule.required_approvers:
                if approver not in self.org.roles and approver != self.company.hitl_default_approver:
                    raise ValueError(
                        f"SoD rule for action '{rule.action}' references unknown role '{approver}'."
                    )
