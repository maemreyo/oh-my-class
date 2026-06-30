from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_FAKE_LLM_IMPORTS: tuple[str, ...] = (
    "FakeListLLM",
    "GenericFakeChatModel",
)


def test_no_forbidden_fake_llm_imports() -> None:
    offenders: list[str] = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        for prohibited in PROHIBITED_FAKE_LLM_IMPORTS:
            if prohibited in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{prohibited}")

    assert offenders == []


def _python_files() -> list[Path]:
    ignored_parts = {".venv", "node_modules", ".git", "__pycache__"}
    guard_file = Path(__file__).resolve()
    return [
        path
        for path in PROJECT_ROOT.rglob("*.py")
        if not ignored_parts.intersection(path.parts) and path.resolve() != guard_file
    ]
