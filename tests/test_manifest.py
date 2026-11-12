import pytest
from pathlib import Path
import tempfile
import yaml

from agent_forge.models.manifest import (
    CompanyManifest,
    CompanySpec,
    DataSourceMap,
    OrgMatrix,
    RoleDefinition,
    SegregationOfDutiesRule,
    WorkflowSaga,
    WorkflowState,
    WorkflowStateType,
    WorkflowTransition,
    ConnectorsConfig,
    ConnectorDefinition,
)


def test_valid_manifest_creation(tmp_path: Path):
    manifest_dir = tmp_path / "test_company"
    manifest_dir.mkdir()
    (manifest_dir / "workflows").mkdir()
    (manifest_dir / "policies").mkdir()

    # company.yaml
    with open(manifest_dir / "company.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "name": "TestCorp",
            "slug": "test-corp",
            "domain": "testcorp.internal",
            "hitl_channel": "telegram",
            "hitl_default_approver": "lead_dev",
        }, f)

    # org_matrix.yaml
    with open(manifest_dir / "org_matrix.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "roles": {
                "lead_dev": {
                    "name": "Lead Developer",
                    "description": "Tech leader",
                    "can_trigger": ["*"],
                },
                "junior_dev": {
                    "name": "Junior Developer",
                    "description": "Code contributor",
                    "can_trigger": ["test_runner"],
                    "forbidden": ["deploy"],
                },
            },
            "segregation_of_duties": [
                {
                    "action": "deploy",
                    "creator_cannot_approve": True,
                    "required_approvers": ["lead_dev"],
                }
            ],
        }, f)

    # data_sources.yaml
    with open(manifest_dir / "data_sources.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "entities": {
                "source_code": {
                    "entity_name": "source_code",
                    "source_of_truth": "github",
                }
            }
        }, f)

    # connectors.yaml
    with open(manifest_dir / "connectors.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "connectors": {
                "github": {
                    "name": "github",
                    "required_env_vars": ["GITHUB_TOKEN"],
                }
            }
        }, f)

    # workflows/dev_saga.yaml
    with open(manifest_dir / "workflows" / "dev_saga.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "name": "dev_saga",
            "description": "CI cycle",
            "initial_state": "start",
            "states": {
                "start": {
                    "name": "start",
                    "state_type": "autonomous",
                    "transitions": [{"condition": "always", "target": "end"}],
                },
                "end": {
                    "name": "end",
                    "state_type": "terminal",
                    "transitions": [],
                },
            },
        }, f)

    manifest = CompanyManifest.load_from_directory(manifest_dir)
    assert manifest.company.name == "TestCorp"
    assert "lead_dev" in manifest.org.roles
    assert "dev_saga" in manifest.workflows


def test_invalid_workflow_state_reference():
    with pytest.raises(ValueError, match="Initial state 'non_existent' is not defined"):
        WorkflowSaga(
            name="broken_workflow",
            description="Broken",
            initial_state="non_existent",
            states={
                "state_a": WorkflowState(
                    name="state_a",
                    state_type=WorkflowStateType.AUTONOMOUS,
                    transitions=[],
                )
            },
        )
