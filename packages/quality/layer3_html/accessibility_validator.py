from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(frozen=True, slots=True)
class AccessibilityValidationResult:
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations


class AccessibilityValidator:
    def validate(self, html: str) -> AccessibilityValidationResult:
        violations: list[str] = []
        if not _has_lang(html):
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
        return AccessibilityValidationResult(violations=violations)


def _has_lang(html: str) -> bool:
    return bool(re.search(r"<html\b[^>]*\blang=[\"'][^\"']+[\"']", html, re.IGNORECASE))


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
