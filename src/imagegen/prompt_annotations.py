"""Prompt annotation validation and provider prompt stripping."""

from __future__ import annotations

import re
from dataclasses import dataclass

from imagegen.palettes import is_valid_name


ANNOTATION_START = re.compile(r"\(([A-Za-z][A-Za-z0-9_-]*):")


@dataclass(frozen=True)
class PromptAnnotation:
    start: int
    end: int
    palette_name: str
    fragment_name: str
    content: str


class PromptAnnotationError(ValueError):
    pass


def validate_prompt_annotations(prompt: str) -> None:
    parse_prompt_annotations(prompt)


def strip_prompt_annotations(prompt: str) -> str:
    annotations = parse_prompt_annotations(prompt)
    if not annotations:
        return prompt

    parts: list[str] = []
    cursor = 0
    for annotation in annotations:
        parts.append(prompt[cursor : annotation.start])
        parts.append(annotation.content)
        cursor = annotation.end
    parts.append(prompt[cursor:])
    return "".join(parts)


def parse_prompt_annotations(prompt: str) -> tuple[PromptAnnotation, ...]:
    annotations: list[PromptAnnotation] = []
    index = 0
    while index < len(prompt):
        if prompt[index] != "(":
            index += 1
            continue

        match = ANNOTATION_START.match(prompt, index)
        if match is None:
            index += 1
            continue

        annotation = _parse_annotation(prompt, match)
        annotations.append(annotation)
        index = annotation.end

    return tuple(annotations)


def _parse_annotation(prompt: str, match: re.Match[str]) -> PromptAnnotation:
    start = match.start()
    palette_name = match.group(1)
    cursor = match.end()

    cursor = _require_whitespace(prompt, cursor)
    fragment_start = cursor
    while (
        cursor < len(prompt) and not prompt[cursor].isspace() and prompt[cursor] != ")"
    ):
        cursor += 1
    fragment_name = prompt[fragment_start:cursor]
    if not is_valid_name(fragment_name):
        raise PromptAnnotationError("Prompt annotation has an invalid fragment name.")

    cursor = _require_whitespace(prompt, cursor)
    content_start = cursor
    content_end = _annotation_content_end(prompt, content_start)
    content = prompt[content_start:content_end]
    if content == "":
        raise PromptAnnotationError("Prompt annotation content is required.")

    return PromptAnnotation(
        start=start,
        end=content_end + 1,
        palette_name=palette_name,
        fragment_name=fragment_name,
        content=content,
    )


def _require_whitespace(prompt: str, cursor: int) -> int:
    if cursor >= len(prompt) or not prompt[cursor].isspace():
        raise PromptAnnotationError(
            "Prompt annotation must use '(palette: fragment content)' syntax."
        )
    while cursor < len(prompt) and prompt[cursor].isspace():
        cursor += 1
    return cursor


def _annotation_content_end(prompt: str, content_start: int) -> int:
    cursor = content_start
    while cursor < len(prompt):
        character = prompt[cursor]
        if character == ")":
            return cursor
        if character == "(":
            raise PromptAnnotationError("Prompt annotations may not be nested.")
        if character == ":":
            raise PromptAnnotationError(
                "Prompt annotation content may not contain ':'."
            )
        cursor += 1
    raise PromptAnnotationError("Prompt annotation is missing a closing ')'.")
