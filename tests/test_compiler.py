import sys
from pathlib import Path
import subprocess
from typer.testing import CliRunner

from agent_forge.cli import app
from agent_forge.models.manifest import CompanyManifest
from agent_forge.compiler.generator import DeploymentCompiler

runner = CliRunner()


def test_cli_init_validate_build(tmp_path: Path):
    manifest_dir = tmp_path / "manifest"
    build_dir = tmp_path / "dist"

    # 1. Test 'agent-forge init'
    res_init = runner.invoke(app, ["init", str(manifest_dir), "--name", "Vortex Labs", "--slug", "vortex-labs"])
    assert res_init.exit_code == 0
    assert (manifest_dir / "company.yaml").exists()
    assert (manifest_dir / "org_matrix.yaml").exists()
    assert (manifest_dir / "data_sources.yaml").exists()
    assert (manifest_dir / "connectors.yaml").exists()
    assert (manifest_dir / "workflows" / "pull_request_delivery.yaml").exists()

    # 2. Test 'agent-forge validate'
    res_val = runner.invoke(app, ["validate", str(manifest_dir)])
    assert res_val.exit_code == 0
    assert "Manifest is valid for: Vortex Labs" in res_val.output

    # 3. Test 'agent-forge build'
    res_build = runner.invoke(app, ["build", str(manifest_dir), "--output", str(build_dir)])
    assert res_build.exit_code == 0
    assert (build_dir / "docker-compose.yml").exists()
    assert (build_dir / "Dockerfile").exists()
    assert (build_dir / "requirements.txt").exists()
    assert (build_dir / ".env.example").exists()
    assert (build_dir / "deploy.sh").exists()
    assert (build_dir / "core" / "state.py").exists()
    assert (build_dir / "core" / "checkpointer.py").exists()
    assert (build_dir / "core" / "llm_client.py").exists()
    assert (build_dir / "core" / "chat_assistant.py").exists()
    assert (build_dir / "core" / "settings_manager.py").exists()
    assert (build_dir / "core" / "dmz_ingress.py").exists()
    assert (build_dir / "core" / "hitl_gateway.py").exists()
    assert (build_dir / "core" / "resilience.py").exists()
    assert (build_dir / "subgraphs" / "pull_request_delivery.py").exists()
    assert (build_dir / "tests" / "test_deployment.py").exists()
    assert (build_dir / "README_AGENT.md").exists()

    # 4. Verify generated tests pass in the compiled project
    test_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(build_dir / "tests" / "test_deployment.py")],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
    )
    assert test_proc.returncode == 0, f"Generated test failed: {test_proc.stderr}\n{test_proc.stdout}"
