from agent_forge.tools.base import (
    BaseTool,
    SafetyLevel,
    ToolExecutionResult,
    ToolRegistry,
)
from agent_forge.tools.packs.dev import (
    ASTCodeAuditor,
    GitCommitMaker,
    GitDiffInspector,
    TestRunnerSandbox,
)
from agent_forge.tools.packs.ops import (
    BashSandbox,
    SafeFileReader,
    SafeFileWriter,
    SendClientEmailTool,
)
from agent_forge.tools.packs.artisan import (
    QuoteCalculatorTool,
    StockInventoryTool,
    BusinessKPISummaryTool,
)
from agent_forge.tools.packs.legal import (
    LegalConflictCheckerTool,
    ProceduralDeadlineCalculatorTool,
    CaseDossierLookupTool,
    LegalCodeRAGSearchTool,
    FeeConventionGeneratorTool,
)


def create_default_registry() -> ToolRegistry:
    """Builds a registry pre-loaded with core engineering, operations, and trade business tools."""
    registry = ToolRegistry()
    # Engineering & Dev
    registry.register(GitDiffInspector())
    registry.register(TestRunnerSandbox())
    registry.register(ASTCodeAuditor())
    registry.register(GitCommitMaker())
    # Ops & Systems
    registry.register(BashSandbox())
    registry.register(SafeFileReader())
    registry.register(SafeFileWriter())
    registry.register(SendClientEmailTool())
    # Artisan & Trade (Quotes, Invoices, Stock, KPIs)
    registry.register(QuoteCalculatorTool())
    registry.register(StockInventoryTool())
    registry.register(BusinessKPISummaryTool())
    # Legal Domain (Case management, conflict checks, deadlines, codes RAG, fee conventions)
    registry.register(LegalConflictCheckerTool())
    registry.register(ProceduralDeadlineCalculatorTool())
    registry.register(CaseDossierLookupTool())
    registry.register(LegalCodeRAGSearchTool())
    registry.register(FeeConventionGeneratorTool())
    return registry


__all__ = [
    "BaseTool",
    "SafetyLevel",
    "ToolExecutionResult",
    "ToolRegistry",
    "create_default_registry",
    "GitDiffInspector",
    "TestRunnerSandbox",
    "ASTCodeAuditor",
    "GitCommitMaker",
    "BashSandbox",
    "SafeFileReader",
    "SafeFileWriter",
    "QuoteCalculatorTool",
    "StockInventoryTool",
    "BusinessKPISummaryTool",
    "LegalConflictCheckerTool",
    "ProceduralDeadlineCalculatorTool",
    "CaseDossierLookupTool",
    "LegalCodeRAGSearchTool",
    "FeeConventionGeneratorTool",
]
