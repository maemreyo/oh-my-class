from __future__ import annotations

import ast
from pathlib import Path
from typing import TypedDict


class ArchitectureSurfaces(TypedDict):
    specialists: dict[str, str]
    unregistered_specialists: list[str]
    renderer_plugins: list[str]
    workers: list[str]
    stores: list[str]
    gate_handlers: list[str]


def collect_architecture_surfaces(root: Path) -> ArchitectureSurfaces:
    root = root.resolve()
    specialist_registry = root / "packages" / "agents" / "teaching_pack" / "specialist_registry.py"
    specialists = _specialist_modules(specialist_registry)
    specialist_directory = specialist_registry.parent / "specialists"
    implemented = {
        _module_name(root, path)
        for path in specialist_directory.glob("*_specialist.py")
    }
    registered = set(specialists.values())
    return {
        "specialists": specialists,
        "unregistered_specialists": sorted(implemented - registered),
        "renderer_plugins": _imported_modules(root / "packages" / "renderer" / "src" / "core" / "runtime.ts"),
        "workers": _module_paths(root, "services/gateway", "*worker.py"),
        "stores": _module_paths(root, "services/gateway", "*store.py"),
        "gate_handlers": _module_paths(root, "packages/agents/gates", "gate_*.py"),
    }


def surface_reachability_errors(root: Path, surfaces: ArchitectureSurfaces) -> list[str]:
    errors: list[str] = []
    for artifact_type, module in sorted(surfaces["specialists"].items()):
        if not _module_path(root, module).is_file():
            errors.append(f"specialist {artifact_type}: registered module is missing: {module}")
    for module in surfaces["unregistered_specialists"]:
        errors.append(f"specialist {module}: no registry entry")
    for module in surfaces["renderer_plugins"]:
        if not _module_path(root, module).is_file():
            errors.append(f"renderer plugin: registered module is missing: {module}")
    for category in ("workers", "stores", "gate_handlers"):
        for module in surfaces.get(category, []):
            if not _module_path(root, module).is_file():
                errors.append(f"{category}: declared module is missing: {module}")
    return errors


def _specialist_modules(registry_path: Path) -> dict[str, str]:
    source = ast.parse(registry_path.read_text(encoding="utf-8"))
    functions = {
        node.name: _imported_python_module(node)
        for node in source.body
        if isinstance(node, ast.FunctionDef) and node.name.endswith("_specialist")
    }
    for node in source.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "SPECIALIST_REGISTRY" and isinstance(node.value, ast.Dict):
            return {
                key.value: module
                for key, value in zip(node.value.keys, node.value.values, strict=True)
                if isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and isinstance(value, ast.Name)
                and value.id in functions
                and (module := functions[value.id]) is not None
            }
    return {}


def _imported_python_module(function: ast.FunctionDef) -> str | None:
    for node in ast.walk(function):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            return node.module
    return None


def _imported_modules(runtime_path: Path) -> list[str]:
    root = runtime_path.parents[4].resolve()
    modules: list[str] = []
    for line in runtime_path.read_text(encoding="utf-8").splitlines():
        if 'from "../plugins/' in line:
            relative = line.split('from "', maxsplit=1)[1].split('"', maxsplit=1)[0]
            modules.append(_module_name(root, (runtime_path.parent / relative).with_suffix(".ts").resolve()))
    return sorted(modules)


def _module_paths(root: Path, relative_directory: str, pattern: str) -> list[str]:
    return sorted(_module_name(root, path) for path in (root / relative_directory).glob(pattern))


def _module_name(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _module_path(root: Path, module: str) -> Path:
    relative = root.joinpath(*module.split("."))
    for suffix in (".py", ".ts"):
        candidate = relative.with_suffix(suffix)
        if candidate.is_file():
            return candidate
    return relative.with_suffix(".py")
