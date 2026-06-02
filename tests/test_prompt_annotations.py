"""Prompt annotation behavior tests.

Behaviors protected:
- Valid prompt annotations parse and strip to provider-ready prompt text.
- Plain prompts remain valid and unchanged.
- Invalid, nested, unterminated, or malformed annotations are rejected.
"""

import pytest

from imagegen.prompt_annotations import (
    PromptAnnotationError,
    parse_prompt_annotations,
    strip_prompt_annotations,
    validate_prompt_annotations,
)


def test_parse_prompt_annotations_finds_one_annotation():
    annotations = parse_prompt_annotations("(character: zoe blue hair)")

    assert len(annotations) == 1
    annotation = annotations[0]
    assert annotation.start == 0
    assert annotation.end == len("(character: zoe blue hair)")
    assert annotation.palette_name == "character"
    assert annotation.fragment_name == "zoe"
    assert annotation.content == "blue hair"


def test_parse_prompt_annotations_finds_multiple_annotations():
    prompt = "portrait of (character: zoe blue hair) in (style: comic_lawrence ink)"

    annotations = parse_prompt_annotations(prompt)

    assert [annotation.palette_name for annotation in annotations] == [
        "character",
        "style",
    ]
    assert [annotation.fragment_name for annotation in annotations] == [
        "zoe",
        "comic_lawrence",
    ]


def test_plain_prompt_without_annotation_marker_is_valid():
    validate_prompt_annotations("a small red house (with a blue roof)")


def test_strip_prompt_annotations_removes_syntax_and_keeps_content():
    prompt = "portrait of (character: zoe blue hair) in (style: photo soft light)"

    stripped = strip_prompt_annotations(prompt)

    assert stripped == "portrait of blue hair in soft light"


def test_strip_prompt_annotations_leaves_plain_prompt_unchanged():
    prompt = "a small red house"

    assert strip_prompt_annotations(prompt) == prompt


def test_validate_prompt_annotations_rejects_unterminated_annotation():
    with pytest.raises(PromptAnnotationError, match="missing a closing"):
        validate_prompt_annotations("(character: zoe blue hair")


def test_validate_prompt_annotations_rejects_nested_annotation():
    with pytest.raises(PromptAnnotationError, match="may not be nested"):
        validate_prompt_annotations("(character: zoe blue (style: photo soft light))")


def test_validate_prompt_annotations_rejects_invalid_fragment_name():
    with pytest.raises(PromptAnnotationError, match="invalid fragment name"):
        validate_prompt_annotations("(character: 1zoe blue hair)")


def test_validate_prompt_annotations_rejects_missing_content():
    with pytest.raises(PromptAnnotationError, match="content is required"):
        validate_prompt_annotations("(character: zoe )")


def test_validate_prompt_annotations_rejects_colon_in_content():
    with pytest.raises(PromptAnnotationError, match="may not contain ':'"):
        validate_prompt_annotations("(character: zoe eye color: blue)")
