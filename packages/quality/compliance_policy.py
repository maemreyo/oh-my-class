from __future__ import annotations

import re
from typing import Final, TypedDict

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class ComplianceResultDict(TypedDict):
    passed: bool
    violations: list[str]
    teacher_reasons: list[str]


COMPLIANCE_HARD_BLOCK_CODES: Final[frozenset[str]] = frozenset({
    "schema_invalid",
    "missing_doctype",
    "external_assets",
    "external_asset",
    "native_radio_inputs",
    "unmanaged_js_runtime",
    "missing_brand_string",
    "contrast_below_aa",
    "missing_alt_text",
    "broken_heading_order",
    "missing_form_label",
    "missing_lang",
    "missing_long_description",
    "answer_key_leakage",
    "pii_leakage",
    "teacher_gate_not_approved",
})

EXTERNAL_ASSET_PATTERNS: Final[tuple[str, ...]] = (
    r'href="https?://',
    r"href='https?://",
    r'src="https?://',
    r"src='https?://",
    r'@import\s+url\(["\']?https?://',
    r'background-image:\s*url\(["\']?https?://',
)

ANSWER_LEAK_PATTERNS: Final[tuple[str, ...]] = (
    r"answer\s*key",
    r"\[\s*answer\s*\]",
    r"correct\s+answer[s]?\s*:",
    r"correct\s+answer[s]?\s+is\s+[A-D0-9]",
    r"[✓✔]\s*correct\s*:",
    r"solution[s]?\s*:",
    r"\banswer[s]?\s*:\s*[A-D0-9]",
    r"đáp\s*án\s*:",
    r"đáp\s*án\s*đúng\s*:",
)

STUDENT_ARTIFACT_TYPES: Final[frozenset[str]] = frozenset({
    "activity_sheet",
    "drill",
    "quiz",
    "recap",
    "student_handout",
    "worksheet",
})


def hard_block_violations(deterministic_issues: list[str], *, teacher_approved: bool) -> list[str]:
    violations = [issue for issue in deterministic_issues if _normalize_issue(issue) in COMPLIANCE_HARD_BLOCK_CODES]
    if not teacher_approved:
        violations.append("teacher_gate_not_approved")
    return violations


def html_hard_blocks(html: str, *, check_answer_key: bool = True) -> tuple[list[str], list[str]]:
    hard_blocks: list[str] = []
    warnings: list[str] = []
    if not check_doctype(html):
        hard_blocks.append("missing_doctype")
    if external_asset_issues(html):
        hard_blocks.append("external_assets")
    if "oh-my-class" not in html.lower():
        hard_blocks.append("missing_brand_string")
    if not check_viewport_meta(html):
        warnings.append("missing_viewport_meta")
    if native_radio_issues(html):
        hard_blocks.append("native_radio_inputs")
    if external_js_issues(html):
        hard_blocks.append("unmanaged_js_runtime")
    if check_answer_key and answer_key_issues(html):
        hard_blocks.append("answer_key_leakage")
    hard_blocks.extend(_accessibility_violations(html))
    return hard_blocks, warnings


def check_doctype(html: str) -> bool:
    return html.strip().upper().startswith("<!DOCTYPE HTML>")


def check_viewport_meta(html: str) -> bool:
    return bool(re.search(r'<meta\s+name=["\']viewport["\']', html, re.IGNORECASE))


def external_asset_issues(html: str) -> list[str]:
    return [f"External asset reference found: {pattern}" for pattern in EXTERNAL_ASSET_PATTERNS if re.findall(pattern, html, re.IGNORECASE)]


def native_radio_issues(html: str) -> list[str]:
    matches = re.findall(r'<input\s+[^>]*type=["\']radio["\']', html, re.IGNORECASE)
    if not matches:
        return []
    return [f"Native radio inputs found: {len(matches)} instances"]


def external_js_issues(html: str) -> list[str]:
    issues: list[str] = []
    if re.findall(r'<script\s+[^>]*src=["\']https?://', html, re.IGNORECASE):
        issues.append("External script references found")
    for display, pattern in (
        ("cdn.tailwindcss.com", r"cdn\.tailwindcss\.com"),
        ("cdnjs.cloudflare.com", r"cdnjs\.cloudflare\.com"),
        ("cdn.jsdelivr.net", r"cdn\.jsdelivr\.net"),
        ("unpkg.com", r"unpkg\.com"),
    ):
        if re.search(pattern, html, re.IGNORECASE):
            issues.append(f"CDN framework detected: {display}")
    return issues


def answer_key_issues(value: str) -> list[str]:
    return [f"Answer key pattern found: '{pattern}'" for pattern in ANSWER_LEAK_PATTERNS if re.findall(pattern, value, re.IGNORECASE)]


def check_artifact_answer_key_leakage(artifact: JsonObject) -> ComplianceResultDict:
    artifact_type = str(artifact.get("artifact_type", artifact.get("type", ""))).lower()
    if artifact_type not in STUDENT_ARTIFACT_TYPES:
        return {"passed": True, "violations": [], "teacher_reasons": []}
    errors = answer_key_issues("\n".join(_collect_text(artifact)))
    return {
        "passed": not errors,
        "violations": ["answer_key_leakage" for _error in errors],
        "teacher_reasons": [f"Answer key leakage detected in {artifact_type}: {error}" for error in errors],
    }


def _collect_text(value: JsonValue) -> list[str]:
    match value:
        case str():
            return [value]
        case dict():
            parts: list[str] = []
            for key, item in value.items():
                # Structural answer-key fields (correct_answer, answer_key) are skipped:
                # they are inherent to quiz/assessment artifacts and are handled by the
                # student_rendered_html check in _snapshot_violations, which is the true
                # student view. Synthesizing "Answer: A" here caused false positives for
                # every quiz regardless of actual student exposure.
                if key in {"answer_key", "correct_answer", "correctAnswer"}:
                    continue
                if key in {"answer", "components", "content", "explain", "explanation", "questions", "rationale", "sections", "text"}:
                    parts.extend(_collect_text(item))
            return parts
        case list():
            return [part for item in value for part in _collect_text(item)]
        case _:
            return []


def _normalize_issue(issue: str) -> str:
    return issue.strip().lower().replace(" ", "_").split(":")[-1].strip()


def _accessibility_violations(html: str) -> list[str]:
    violations: list[str] = []
    if not re.search(r"<html\b[^>]*\blang=[\"'][^\"']+[\"']", html, re.IGNORECASE):
        violations.append("missing_lang")
    if _images_missing_alt(html):
        violations.append("missing_alt_text")
    if _svg_missing_long_description(html):
        violations.append("missing_long_description")
    if _has_broken_heading_order(html):
        violations.append("broken_heading_order")
    if _forms_missing_labels(html):
        violations.append("missing_form_label")
    if _has_low_contrast(html):
        violations.append("contrast_below_aa")
    return violations


def _images_missing_alt(html: str) -> bool:
    for tag in re.findall(r"<img\b[^>]*>", html, re.IGNORECASE):
        if _has_attr(tag, "aria-hidden", "true"):
            continue
        if not re.search(r"\balt=[\"'][^\"']*[\"']", tag, re.IGNORECASE):
            return True
    return False


def _svg_missing_long_description(html: str) -> bool:
    for tag in re.findall(r"<svg\b[^>]*>", html, re.IGNORECASE):
        decorative = _has_attr(tag, "aria-hidden", "true")
        has_label = re.search(r"\baria-label=[\"'][^\"']+[\"']", tag, re.IGNORECASE)
        has_long_description = re.search(
            r"\b(data-long-description|aria-describedby)=[\"'][^\"']+[\"']",
            tag,
            re.IGNORECASE,
        )
        if not decorative and (not has_label or not has_long_description):
            return True
    return False


def _has_broken_heading_order(html: str) -> bool:
    levels = [int(level) for level in re.findall(r"<h([1-6])\b", html, re.IGNORECASE)]
    previous = 0
    for level in levels:
        if previous and level > previous + 1:
            return True
        previous = level
    return False


def _forms_missing_labels(html: str) -> bool:
    labelled_ids = set(re.findall(r"<label\b[^>]*\bfor=[\"']([^\"']+)[\"']", html, re.IGNORECASE))
    fields = re.findall(r"<(input|select|textarea)\b[^>]*>", html, re.IGNORECASE)
    for field_type in fields:
        for tag in re.findall(rf"<{field_type}\b[^>]*>", html, re.IGNORECASE):
            if _is_non_text_control(tag):
                continue
            field_id = _attr_value(tag, "id")
            has_label = field_id is not None and field_id in labelled_ids
            has_aria = _attr_value(tag, "aria-label") is not None or _attr_value(tag, "aria-labelledby") is not None
            if not has_label and not has_aria:
                return True
    return False


def _has_low_contrast(html: str) -> bool:
    for tag in re.findall(r"<[^>]+style=[\"'][^\"']+[\"'][^>]*>", html, re.IGNORECASE):
        color = _style_hex(tag, "color")
        background = _style_hex(tag, "background-color")
        if color is None or background is None:
            continue
        if _contrast_ratio(color, background) < 4.5:
            return True
    return False


def _is_non_text_control(tag: str) -> bool:
    input_type = (_attr_value(tag, "type") or "text").lower()
    return input_type in {"hidden", "submit", "button", "reset", "image"}


def _has_attr(tag: str, name: str, value: str) -> bool:
    return (_attr_value(tag, name) or "").lower() == value


def _attr_value(tag: str, name: str) -> str | None:
    match = re.search(rf"\b{name}=[\"']([^\"']*)[\"']", tag, re.IGNORECASE)
    return None if match is None else match.group(1)


def _style_hex(tag: str, property_name: str) -> str | None:
    match = re.search(rf"{property_name}\s*:\s*(#[0-9a-f]{{6}})\b", tag, re.IGNORECASE)
    return None if match is None else match.group(1)


def _contrast_ratio(foreground: str, background: str) -> float:
    fg = _relative_luminance(foreground)
    bg = _relative_luminance(background)
    lighter = max(fg, bg)
    darker = min(fg, bg)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(hex_color: str) -> float:
    red, green, blue = (int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5))
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def _linear(channel: float) -> float:
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4
