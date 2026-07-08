from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_FAKE_LLM_IMPORTS: tuple[str, ...] = (
    "FakeListLLM",
    "GenericFakeChatModel",
)

# Repo-local fake-LLM doubles. Using these is fine in ordinary (non-real_llm)
# tests — the testing pyramid explicitly allows deterministic logic to be
# tested without a real LLM. The violation is using one of these IN THE SAME
# FILE as a `real_llm` marker: that combination means a test claims to prove
# real-9router behavior while secretly never calling it.
FAKE_LLM_DOUBLES: tuple[str, ...] = (
    "MockLLMClient",
    "FakeLLMClient",
    "FakeListLLM",
    "GenericFakeChatModel",
)
# Ad-hoc mock patterns that fake the litellm/openai/9router transport itself
# (e.g. `patch.dict(sys.modules, {"litellm": MagicMock()})`) — a real_llm file
# doing this never actually calls 9router, same violation as FAKE_LLM_DOUBLES.
FAKE_TRANSPORT_PATCH_MARKERS: tuple[str, ...] = (
    '{"litellm":',
    "patch(\"litellm",
    "patch('litellm",
    "patch.object(litellm",
)
REAL_LLM_MARKER = "pytest.mark.real_llm"


def test_no_forbidden_fake_llm_imports() -> None:
    offenders: list[str] = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        for prohibited in PROHIBITED_FAKE_LLM_IMPORTS:
            if prohibited in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{prohibited}")

    assert offenders == []


def test_no_real_llm_marker_alongside_fake_llm_double() -> None:
    """A file cannot claim `real_llm` while also using a fake-LLM double.

    Catches the exact bug found 2026-07-08: a file-level
    `pytestmark = pytest.mark.real_llm` with individual tests that mock
    `litellm`/`MockLLMClient` instead of calling 9router. File-granularity
    (not per-function AST) is deliberate — see .scratch grill notes for the
    tradeoff; upgrade to per-function analysis only if a real file mixes
    genuine real_llm tests with unrelated mock-based tests.
    """
    offenders: list[str] = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        if REAL_LLM_MARKER not in text:
            continue
        for double in FAKE_LLM_DOUBLES:
            if double in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{double}")
        for marker in FAKE_TRANSPORT_PATCH_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{marker}")

    assert offenders == [], (
        f"real_llm-marked file(s) also fake the LLM transport: {offenders}"
    )


def _python_files() -> list[Path]:
    ignored_parts = {".venv", "node_modules", ".git", "__pycache__"}
    guard_file = Path(__file__).resolve()
    return [
        path
        for path in PROJECT_ROOT.rglob("*.py")
        if not ignored_parts.intersection(path.parts) and path.resolve() != guard_file
    ]
