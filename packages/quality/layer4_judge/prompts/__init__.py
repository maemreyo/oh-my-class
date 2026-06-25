from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_system_prompt(name: str = "system") -> str:
	path = _PROMPTS_DIR / f"{name}.md"
	if not path.exists():
		raise FileNotFoundError(f"Prompt not found: {path}")
	return path.read_text(encoding="utf-8")
