from __future__ import annotations

import re

from common.contracts.artifact import ArtifactContent

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

_PLACEHOLDER_PATTERN = re.compile(r"\b(?:todo|placeholder|lorem ipsum|tbd)\b|\[tbd\]", re.IGNORECASE)
_ANSWER_KEY_PATTERN = re.compile(r"\b(?:answer key|answer:|correct:|solution:)", re.IGNORECASE)
_TOKEN_PATTERN = re.compile(r"[a-z][a-z0-9]{3,}", re.IGNORECASE)
_STRUCTURAL_TERMS = frozenset({
    "accessibility",
    "content",
    "lesson",
    "metadata",
    "question",
    "quiz",
    "section",
    "sections",
    "theme",
    "title",
    "type",
})
_VI_DIFFICULTY_KEYS = frozenset({"nhan_biet", "thong_hieu", "van_dung", "van_dung_cao"})
_VI_DIFFICULTY_TARGETS = {
    "nhan_biet": 0.4,
    "thong_hieu": 0.3,
    "van_dung": 0.2,
    "van_dung_cao": 0.1,
}


class TeachingPackQualityGateError(RuntimeError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("Teaching Pack quality gate failed: " + "; ".join(issues))


def quality_issues(artifacts: list[JsonObject]) -> list[str]:
    issues: list[str] = []
    parsed_artifacts: list[ArtifactContent] = []
    for index, artifact in enumerate(artifacts):
        try:
            parsed = ArtifactContent.model_validate(artifact)
        except ValueError as exc:
            issues.append(f"artifacts[{index}]: schema_invalid: {exc}")
            continue
        parsed_artifacts.append(parsed)
        issues.extend(_artifact_quality_issues(index, parsed))
    issues.extend(_pack_coherence_issues(parsed_artifacts))
    return issues


def _artifact_quality_issues(index: int, artifact: ArtifactContent) -> list[str]:
    issues: list[str] = []
    if _PLACEHOLDER_PATTERN.search(artifact.title):
        issues.append(f"artifacts[{index}].title: placeholder_content")
    for section_index, section in enumerate(artifact.sections):
        if section.get("teacher_only") is True:
            continue
        section_text = str(section)
        if _PLACEHOLDER_PATTERN.search(section_text):
            issues.append(f"artifacts[{index}].sections[{section_index}]: placeholder_content")
        if _ANSWER_KEY_PATTERN.search(section_text):
            issues.append(f"artifacts[{index}].sections[{section_index}]: answer_key_leakage")
    if not artifact.accessibility.get("language"):
        issues.append(f"artifacts[{index}].accessibility.language: missing")
    return issues


def _pack_coherence_issues(artifacts: list[ArtifactContent]) -> list[str]:
    lesson = _artifact_by_type(artifacts, "lesson")
    if lesson is None:
        return []
    issues: list[str] = []
    lesson_terms = _content_terms(lesson)
    lesson_objective_terms = _objective_terms(lesson)
    lesson_vocabulary = _metadata_terms(lesson, "key_terms")
    for artifact in artifacts:
        if artifact.artifact_type == "lesson":
            continue
        artifact_terms = _content_terms(artifact)
        if artifact.artifact_type == "quiz" and lesson_terms and artifact_terms and lesson_terms.isdisjoint(artifact_terms):
            issues.append("pack.coherence: quiz_not_aligned_with_lesson")
        if lesson_objective_terms and artifact_terms and lesson_objective_terms.isdisjoint(artifact_terms):
            issues.append(f"pack.coherence: {artifact.artifact_type}_not_aligned_with_objectives")
        if lesson_vocabulary and artifact.artifact_type in {"quiz", "worksheet"}:
            missing_terms = sorted(lesson_vocabulary - artifact_terms)
            if missing_terms:
                issues.append(f"pack.coherence: {artifact.artifact_type}_missing_lesson_vocabulary")
    if _is_vietnamese_pack(lesson):
        quiz = _artifact_by_type(artifacts, "quiz")
        if quiz is not None:
            issues.extend(_vietnamese_difficulty_issues(quiz))
    return issues


def _objective_terms(lesson: ArtifactContent) -> set[str]:
    objectives = lesson.metadata.get("learning_objectives")
    if not isinstance(objectives, list):
        return set()
    return _terms_from_values(objectives)


def _metadata_terms(artifact: ArtifactContent, key: str) -> set[str]:
    values = artifact.metadata.get(key)
    if not isinstance(values, list):
        return set()
    return _terms_from_values(values)


def _terms_from_values(values: list[JsonValue]) -> set[str]:
    return {
        token.lower()
        for value in values
        for token in _TOKEN_PATTERN.findall(str(value))
        if token.lower() not in _STRUCTURAL_TERMS
    }


def _is_vietnamese_pack(lesson: ArtifactContent) -> bool:
    language = str(lesson.accessibility.get("language") or lesson.metadata.get("locale") or "").lower()
    return language.startswith("vi")


def _vietnamese_difficulty_issues(quiz: ArtifactContent) -> list[str]:
    distribution = quiz.metadata.get("difficulty_distribution")
    if not isinstance(distribution, dict):
        return []
    normalized = {str(key): value for key, value in distribution.items()}
    if not _VI_DIFFICULTY_KEYS.issubset(normalized):
        return ["pack.coherence: quiz_missing_vietnamese_difficulty_distribution"]
    for key, target in _VI_DIFFICULTY_TARGETS.items():
        value = normalized[key]
        if not isinstance(value, int | float):
            return ["pack.coherence: quiz_invalid_vietnamese_difficulty_distribution"]
        if abs(float(value) - target) > 0.05:
            return ["pack.coherence: quiz_invalid_vietnamese_difficulty_distribution"]
    return []


def _artifact_by_type(artifacts: list[ArtifactContent], artifact_type: str) -> ArtifactContent | None:
    for artifact in artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def _content_terms(artifact: ArtifactContent) -> set[str]:
    text_parts = [artifact.title]
    for section in artifact.sections:
        if section.get("teacher_only") is True:
            continue
        text_parts.append(str(section))
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(" ".join(text_parts))
        if token.lower() not in _STRUCTURAL_TERMS
    }
