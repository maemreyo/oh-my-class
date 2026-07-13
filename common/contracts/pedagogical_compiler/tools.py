"""#494: registry-driven governed domain-tool runtime."""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import Field

from common.contracts.pedagogical_compiler.common import FrozenContract, canonical_json, stable_hash, stable_id

ToolStatus = Literal["verified", "unsupported", "invalid_input", "timeout", "failed", "uncertain"]


class ToolCapability(FrozenContract):
    tool_id: str
    version: str
    subjects: tuple[str, ...]
    grade_bands: tuple[str, ...]
    languages: tuple[str, ...]
    deterministic: bool
    network_policy: Literal["none", "allowlisted"] = "none"
    sandbox_policy: str = "pure_function"
    timeout_seconds: float = Field(default=1.0, gt=0, le=30)
    supported_claims: tuple[str, ...]


class ToolBudget(FrozenContract):
    timeout_seconds: float = Field(default=1.0, gt=0, le=30)
    max_output_bytes: int = Field(default=8_192, ge=128, le=1_000_000)


class ToolPolicy(FrozenContract):
    policy_version: str
    prefer_deterministic: bool = True
    allow_network: bool = False


class ToolRequest(FrozenContract):
    request_id: str
    tool_id: str
    input: dict[str, Any]
    tenant_scope: str
    policy: ToolPolicy
    budget: ToolBudget = ToolBudget()


class ToolEvidence(FrozenContract):
    evidence_id: str
    normalized_input_hash: str
    result_hash: str
    statement: str


class ToolFailure(FrozenContract):
    code: ToolStatus
    message: str


class ToolResult(FrozenContract):
    status: ToolStatus
    output: dict[str, Any] | None = None
    evidence: ToolEvidence | None = None
    failure: ToolFailure | None = None


class ToolReceipt(FrozenContract):
    receipt_id: str
    tool_id: str
    tool_version: str
    tenant_scope: str
    policy_version: str
    normalized_input_hash: str
    result_hash: str | None
    status: ToolStatus
    reusable: bool


@dataclass(slots=True)
class DomainToolRuntime:
    capabilities: dict[str, ToolCapability] = field(default_factory=dict)
    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = field(default_factory=dict)
    cache: dict[tuple[str, str, str, str, str], tuple[ToolResult, ToolReceipt]] = field(default_factory=dict)

    def register(self, capability: ToolCapability, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        if capability.tool_id in self.capabilities:
            raise ValueError(f"duplicate tool capability {capability.tool_id}")
        self.capabilities[capability.tool_id] = capability
        self.handlers[capability.tool_id] = handler

    def execute(self, request: ToolRequest) -> tuple[ToolResult, ToolReceipt]:
        capability = self.capabilities.get(request.tool_id)
        input_hash = stable_hash("tool-input", request.input)
        if capability is None:
            result = ToolResult(status="unsupported", failure=ToolFailure(code="unsupported", message="tool capability is not registered"))
            return result, _receipt(request, "unregistered", input_hash, result)
        if capability.network_policy != "none" and not request.policy.allow_network:
            result = ToolResult(status="unsupported", failure=ToolFailure(code="unsupported", message="network tool denied by policy"))
            return result, _receipt(request, capability.version, input_hash, result)
        cache_key = (request.tenant_scope, request.tool_id, capability.version, request.policy.policy_version, input_hash)
        if capability.deterministic and cache_key in self.cache:
            return self.cache[cache_key]
        try:
            output = self.handlers[request.tool_id](request.input)
            encoded = canonical_json(output).encode("utf-8")
            if len(encoded) > request.budget.max_output_bytes:
                raise ValueError("tool output exceeds budget")
            result_hash = stable_hash("tool-result", output)
            evidence = ToolEvidence(
                evidence_id=stable_id("tool-evidence", request.tool_id, capability.version, input_hash, result_hash),
                normalized_input_hash=input_hash,
                result_hash=result_hash,
                statement=f"Verified by deterministic tool {request.tool_id}@{capability.version}",
            )
            result = ToolResult(status="verified", output=output, evidence=evidence)
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
            result = ToolResult(status="invalid_input", failure=ToolFailure(code="invalid_input", message=str(exc)[:500]))
        except Exception as exc:  # defensive runtime boundary
            result = ToolResult(status="failed", failure=ToolFailure(code="failed", message=type(exc).__name__))
        receipt = _receipt(request, capability.version, input_hash, result)
        if capability.deterministic and result.status == "verified":
            self.cache[cache_key] = (result, receipt)
        return result, receipt


def default_tool_runtime() -> DomainToolRuntime:
    runtime = DomainToolRuntime()
    runtime.register(ToolCapability(
        tool_id="arithmetic", version="arithmetic.v1", subjects=("math", "science"),
        grade_bands=("k_2", "grades_3_5", "grades_6_8", "grades_9_12"), languages=("en", "vi"),
        deterministic=True, supported_claims=("numeric_answer", "arithmetic_equivalence"),
    ), _arithmetic)
    runtime.register(ToolCapability(
        tool_id="readability", version="readability.v1", subjects=("all",),
        grade_bands=("k_2", "grades_3_5", "grades_6_8", "grades_9_12"), languages=("en", "vi"),
        deterministic=True, supported_claims=("word_count", "sentence_count", "average_sentence_length"),
    ), _readability)
    return runtime


def _receipt(request: ToolRequest, version: str, input_hash: str, result: ToolResult) -> ToolReceipt:
    result_hash = result.evidence.result_hash if result.evidence else None
    return ToolReceipt(
        receipt_id=stable_id("tool-receipt", request.tenant_scope, request.tool_id, version, input_hash, result.status, result_hash),
        tool_id=request.tool_id,
        tool_version=version,
        tenant_scope=request.tenant_scope,
        policy_version=request.policy.policy_version,
        normalized_input_hash=input_hash,
        result_hash=result_hash,
        status=result.status,
        reusable=result.status == "verified",
    )


def _arithmetic(payload: dict[str, Any]) -> dict[str, Any]:
    expression = payload.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression is required")
    tree = ast.parse(expression, mode="eval")
    value = _eval_node(tree.body)
    if not math.isfinite(float(value)):
        raise ValueError("non-finite result")
    return {"expression": expression, "value": value}


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Add): return left + right
        if isinstance(node.op, ast.Sub): return left - right
        if isinstance(node.op, ast.Mult): return left * right
        if isinstance(node.op, ast.Div): return left / right
        if isinstance(node.op, ast.FloorDiv): return left // right
        if isinstance(node.op, ast.Mod): return left % right
        if abs(float(right)) > 12:
            raise ValueError("exponent exceeds deterministic tool bound")
        return left ** right
    raise ValueError("unsupported arithmetic syntax")


def _readability(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    words = text.split()
    sentences = [part for part in text.replace("!", ".").replace("?", ".").split(".") if part.strip()]
    return {
        "word_count": len(words),
        "sentence_count": max(1, len(sentences)),
        "average_sentence_length": round(len(words) / max(1, len(sentences)), 3),
    }
