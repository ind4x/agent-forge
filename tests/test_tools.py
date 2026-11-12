from pathlib import Path
import pytest

from agent_forge.tools import (
    ASTCodeAuditor,
    GitCommitMaker,
    SafeFileReader,
    SafeFileWriter,
    create_default_registry,
    SafetyLevel,
)


def test_default_registry():
    registry = create_default_registry()
    tools = registry.list_all()
    assert len(tools) >= 7

    read_tools = registry.list_by_safety(SafetyLevel.READ_ONLY)
    assert any(t.name == "safe_file_reader" for t in read_tools)

    filtered = registry.filter_for_role(
        can_trigger=["safe_file_reader", "ast_code_auditor"],
        forbidden=["safe_file_writer"],
    )
    names = [t.name for t in filtered]
    assert "safe_file_reader" in names
    assert "ast_code_auditor" in names
    assert "safe_file_writer" not in names


def test_ast_code_auditor(tmp_path: Path):
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    auditor = ASTCodeAuditor()
    res = auditor.run(file_path=str(clean_file))
    assert res.success is True
    assert res.output["syntax_valid"] is True
    assert res.output["total_findings"] == 0

    dirty_file = tmp_path / "dirty.py"
    dirty_file.write_text("try:\n    x = 1\nexcept:\n    breakpoint()\n", encoding="utf-8")
    dirty_res = auditor.run(file_path=str(dirty_file))
    assert dirty_res.success is True
    assert dirty_res.output["total_findings"] >= 2


def test_safe_file_reader_and_writer(tmp_path: Path):
    writer = SafeFileWriter()
    reader = SafeFileReader()

    target_file = tmp_path / "sample.txt"
    write_res = writer.run(path=str(target_file), content="Hello, Enterprise!", create_backup=True)
    assert write_res.success is True
    assert target_file.exists()

    # Overwrite to trigger backup creation
    write_res_2 = writer.run(path=str(target_file), content="Second edition", create_backup=True)
    assert write_res_2.success is True
    assert write_res_2.output["backup_created"] is not None

    read_res = reader.run(path=str(target_file))
    assert read_res.success is True
    assert read_res.output["content"] == "Second edition"


def test_conventional_commit_checker():
    maker = GitCommitMaker()
    # Invalid message should raise ValueError
    res = maker.run(message="random commit without convention")
    assert res.success is False
    assert "Conventional Commits" in (res.error or "")
