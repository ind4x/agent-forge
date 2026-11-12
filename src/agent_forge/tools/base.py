from abc import ABC, abstractmethod
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class SafetyLevel(str, Enum):
    READ_ONLY = "read_only"
    MUTATING_SAFE = "mutating_safe"
    CRITICAL_HITL = "critical_hitl"


class ToolExecutionResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BaseTool(ABC):
    name: str
    description: str
    category: str
    safety_level: SafetyLevel
    args_schema: Type[BaseModel]

    def run(self, **kwargs: Any) -> ToolExecutionResult:
        """Validates arguments against Pydantic schema and wraps execution in execution telemetry."""
        start_time = time.perf_counter()
        try:
            validated_args = self.args_schema(**kwargs)
            res = self.execute(**validated_args.model_dump())
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ToolExecutionResult(
                success=True,
                output=res,
                execution_time_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return ToolExecutionResult(
                success=False,
                error=f"{type(exc).__name__}: {str(exc)}",
                execution_time_ms=elapsed,
            )

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Concrete execution logic implemented by tool packs."""
        raise NotImplementedError

    def to_function_definition(self) -> Dict[str, Any]:
        """Exports tool definition compatible with LangGraph and OpenAI/Anthropic tool schemas."""
        schema = self.args_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
            "safety_level": self.safety_level.value,
            "category": self.category,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_all(self) -> List[BaseTool]:
        return list(self._tools.values())

    def list_by_category(self, category: str) -> List[BaseTool]:
        return [t for t in self._tools.values() if t.category == category]

    def list_by_safety(self, safety: SafetyLevel) -> List[BaseTool]:
        return [t for t in self._tools.values() if t.safety_level == safety]

    def filter_for_role(
        self,
        can_trigger: List[str],
        forbidden: List[str],
    ) -> List[BaseTool]:
        """Filters registered tools according to a role's authorization matrix."""
        allowed: List[BaseTool] = []
        allow_all = "*" in can_trigger
        for tool in self._tools.values():
            if tool.name in forbidden:
                continue
            if allow_all or tool.name in can_trigger or tool.category in can_trigger:
                allowed.append(tool)
        return allowed
